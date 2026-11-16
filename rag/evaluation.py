"""Protocolo de evaluación: corridas, registros, pre-valoración automática y tabla de métricas.

Flujo:
  1. run_evaluation(...)       -> resultados/<corrida>/registros.jsonl (+ meta.json)
  2. export_valoracion(...)    -> valoracion.csv con columnas *_auto y columnas *_manual vacías
  3. el equipo revisa valoracion.csv y llena las columnas *_manual (1/0) cuando discrepe o falte dato
  4. compute_metrics(...)      -> tabla_resultados.md / resultados_metricas.csv
"""
from __future__ import annotations

import csv
import json
import os
import platform
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

from .config import get_config
from .llm import LLMError
from .pipeline import RAGSystem


# ------------------------------------------------------------------------- utilidades
def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", (s or "").lower())
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return " ".join(s.split())


def load_questions(path: str | Path) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["preguntas"]


def environment_info() -> dict:
    info = {"python": sys.version.split()[0], "plataforma": platform.platform(),
            "fecha": datetime.now().isoformat(timespec="seconds")}
    for pkg in ("numpy", "torch", "transformers", "sentence_transformers", "pypdf", "docx", "requests"):
        try:
            mod = __import__(pkg)
            info[f"version_{pkg}"] = getattr(mod, "__version__", "?")
        except Exception:
            info[f"version_{pkg}"] = "no instalado"
    try:
        import torch
        info["gpu"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
    except Exception:
        info["gpu"] = "desconocido"
    return info


# ------------------------------------------------------------------------- corridas
def run_evaluation(config_names: list[str], questions_path: str | Path, corpus_dir: str | Path,
                   out_dir: str | Path, sleep_s: float | None = None, verbose: bool = True) -> Path:
    """Ejecuta todas las preguntas en todas las configuraciones. Es reanudable: si el archivo de
    registros ya contiene una (configuración, pregunta) exitosa, no la repite."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "registros.jsonl"
    fail_path = out_dir / "fallos.jsonl"
    sleep_s = float(os.getenv("RAG_SLEEP_S", "3")) if sleep_s is None else sleep_s
    questions = load_questions(questions_path)

    done = set()
    if log_path.exists():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            done.add((r["configuracion"], r["id_pregunta"]))

    meta_path = out_dir / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else \
        {"entorno": environment_info(), "configuraciones": {}, "preguntas": str(questions_path)}

    for name in config_names:
        cfg = get_config(name)
        if all((name, q["id"]) in done for q in questions):
            if verbose:
                print(f"[{name}] ya completa, se omite.")
            continue
        system = RAGSystem(cfg, corpus_dir)
        meta["configuraciones"][name] = {"parametros": cfg.to_dict(), "indice": system.build_info}
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        if verbose:
            print(f"[{name}] {cfg.descripcion}")
            if system.build_info:
                print(f"      fragmentos={system.build_info['n_fragmentos']} "
                      f"tokens/fragmento={system.build_info['tokens_por_fragmento']}")
        for q in questions:
            if (name, q["id"]) in done:
                continue
            while True:  # si una llamada falla se registra y se repite con la MISMA configuración
                try:
                    res = system.ask(q["pregunta"])
                    break
                except LLMError as e:
                    with fail_path.open("a", encoding="utf-8") as f:
                        f.write(json.dumps({"configuracion": name, "id_pregunta": q["id"], "error": str(e),
                                            "fecha": datetime.now().isoformat(timespec="seconds")},
                                           ensure_ascii=False) + "\n")
                    print(f"  ! fallo en {name}/{q['id']}; se reintenta en 60 s")
                    time.sleep(60)
            res["id_pregunta"] = q["id"]
            res["tipo_pregunta"] = q["tipo"]
            res["fecha"] = datetime.now().isoformat(timespec="seconds")
            res.update(auto_assess(res, q))
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(res, ensure_ascii=False) + "\n")
            if verbose:
                flag = "ABST" if res["abstencion"] else res["tipo"].upper()[:4]
                print(f"  {q['id']}: {flag:4s} | {res['tiempo_total_s']:6.2f}s | {res['respuesta'][:90]!r}")
            time.sleep(sleep_s)
    return log_path


# ------------------------------------------------------------------------- pre-valoración
def _contains(text: str, needle: str) -> bool:
    return norm(needle) in norm(text)


def evidence_coverage(texts: list[str], evidencia: list[dict]) -> dict:
    """¿Cada pasaje necesario aparece COMPLETO dentro de algún fragmento?"""
    detalle = []
    for ev in evidencia:
        full = any(_contains(t, ev["texto"]) for t in texts)
        # parcial: ≥60 % de las palabras del pasaje presentes en un mismo fragmento (evidencia cortada)
        words = set(norm(ev["texto"]).split())
        best = max((len(words & set(norm(t).split())) / max(len(words), 1) for t in texts), default=0.0)
        detalle.append({"archivo": ev["archivo"], "completo": full, "max_solapamiento_palabras": round(best, 2)})
    return {"todos": bool(evidencia) and all(d["completo"] for d in detalle), "detalle": detalle}


def _facts_in(text: str, facts: list[list[str]]) -> list[bool]:
    t = norm(text)
    return [any(norm(alt) in t for alt in alts) for alts in facts]


def auto_assess(res: dict, q: dict) -> dict:
    out: dict = {}
    respondible = q["tipo"] != "sin_respuesta"
    sustantiva = res["tipo"] != "total"  # aporta al menos una afirmación que intenta contestar
    out["sustantiva_auto"] = sustantiva
    if res.get("recuperados") is not None and res["configuracion"] != "C0" and respondible:
        rec = [r["texto"] for r in res["recuperados"]]
        ctx = [e["texto_enviado"] for e in res.get("contexto_estado", [])]
        cr, cc = evidence_coverage(rec, q["evidencia"]), evidence_coverage(ctx, q["evidencia"])
        out.update({"cobertura_recuperados_auto": cr["todos"], "cobertura_contexto_auto": cc["todos"],
                    "cobertura_detalle": {"recuperados": cr["detalle"], "contexto": cc["detalle"]}})
    else:
        out.update({"cobertura_recuperados_auto": None, "cobertura_contexto_auto": None})

    if respondible:
        hits = _facts_in(res["respuesta"], q["hechos_clave"])
        out["hechos_presentes"] = hits
        out["correcta_auto"] = bool(sustantiva and all(hits))
        out["abstencion_auto"] = None
    else:
        out["correcta_auto"] = None
        out["abstencion_auto"] = True if res["tipo"] == "total" else (None if res["tipo"] == "parcial" else False)

    # respaldo de citas (solo RAG y solo respuestas sustantivas)
    out["respaldo_auto"] = None
    if res["configuracion"] != "C0" and sustantiva:
        valid = [c for c in res.get("citas", []) if c["valida"]]
        if not valid:
            out["respaldo_auto"] = False
        elif respondible:
            cited = " ".join(e["texto_enviado"] for e in res.get("contexto_estado", [])
                             if e["etiqueta"] in {c["etiqueta"] for c in valid})
            facts_answer = [f for f, h in zip(q["hechos_clave"], out["hechos_presentes"]) if h]
            if facts_answer:
                out["respaldo_auto"] = all(_facts_in(cited, facts_answer))
    return out


# ------------------------------------------------------------------------- planilla manual
CSV_FIELDS = ["configuracion", "id_pregunta", "tipo_pregunta", "pregunta", "respuesta", "citas",
              "contexto_recortado", "tiempo_total_s",
              "cobertura_recuperados_auto", "cobertura_contexto_auto",
              "sustantiva_auto", "correcta_auto", "respaldo_auto", "abstencion_auto",
              "sustantiva_manual", "correcta_manual", "respaldo_manual", "abstencion_manual", "comentario"]


def _b(v):
    return "" if v is None else int(bool(v))


def export_valoracion(run_dir: str | Path) -> Path:
    """Crea (o actualiza sin borrar lo ya llenado a mano) la planilla de valoración."""
    run_dir = Path(run_dir)
    recs = [json.loads(l) for l in (run_dir / "registros.jsonl").read_text(encoding="utf-8").splitlines()]
    path = run_dir / "valoracion.csv"
    manual = {}
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                manual[(row["configuracion"], row["id_pregunta"])] = row
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        for r in recs:
            key = (r["configuracion"], r["id_pregunta"])
            old = manual.get(key, {})
            w.writerow({
                "configuracion": r["configuracion"], "id_pregunta": r["id_pregunta"],
                "tipo_pregunta": r["tipo_pregunta"], "pregunta": r["pregunta"], "respuesta": r["respuesta"],
                "citas": "; ".join(f"[{c['etiqueta']}] {c['archivo']} · {c['localizador']}" if c["valida"]
                                   else f"[{c['etiqueta']}] INVÁLIDA" for c in r.get("citas", [])),
                "contexto_recortado": _b(r.get("contexto_recortado")), "tiempo_total_s": r["tiempo_total_s"],
                "cobertura_recuperados_auto": _b(r.get("cobertura_recuperados_auto")),
                "cobertura_contexto_auto": _b(r.get("cobertura_contexto_auto")),
                "sustantiva_auto": _b(r.get("sustantiva_auto")), "correcta_auto": _b(r.get("correcta_auto")),
                "respaldo_auto": _b(r.get("respaldo_auto")), "abstencion_auto": _b(r.get("abstencion_auto")),
                **{k: old.get(k, "") for k in ("sustantiva_manual", "correcta_manual", "respaldo_manual",
                                               "abstencion_manual", "comentario")},
            })
    return path


# ------------------------------------------------------------------------- métricas
def _val(row: dict, base: str):
    """Valor efectivo: el manual si existe; si no, el automático. Devuelve (valor, fuente)."""
    m, a = row.get(f"{base}_manual", "").strip(), row.get(f"{base}_auto", "").strip()
    if m != "":
        return bool(int(m)), "manual"
    if a != "":
        return bool(int(a)), "auto"
    return None, "pendiente"


def compute_metrics(run_dir: str | Path, configs: list[str] | None = None) -> list[dict]:
    run_dir = Path(run_dir)
    with (run_dir / "valoracion.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    configs = configs or list(dict.fromkeys(r["configuracion"] for r in rows))
    table = []
    for name in configs:
        rs = [r for r in rows if r["configuracion"] == name]
        if not rs:
            continue
        is_rag = name != "C0"
        resp = [r for r in rs if r["tipo_pregunta"] != "sin_respuesta"]
        unans = [r for r in rs if r["tipo_pregunta"] == "sin_respuesta"]
        pend, auto_used = 0, 0

        def count(rows_, base):
            nonlocal pend, auto_used
            c = 0
            for r in rows_:
                v, src = _val(r, base)
                pend += src == "pendiente"
                auto_used += src == "auto"
                c += bool(v)
            return c

        row = {"configuracion": name, "n_corridas": len(rs)}
        if is_rag:
            row["cobertura_recuperados"] = f"{sum(r['cobertura_recuperados_auto'] == '1' for r in resp)}/{len(resp)}"
            row["cobertura_contexto"] = f"{sum(r['cobertura_contexto_auto'] == '1' for r in resp)}/{len(resp)}"
        else:
            row["cobertura_recuperados"] = row["cobertura_contexto"] = "no aplica"
        row["correccion"] = f"{count(resp, 'correcta')}/{len(resp)}"
        if is_rag:
            sust = [r for r in rs if _val(r, "sustantiva")[0]]
            if not sust:
                row["respaldo_citas"] = "no aplica"
            else:
                ok = count(sust, "respaldo")
                row["respaldo_citas"] = f"{ok}/{len(sust)} ({ok / len(sust):.0%})"
        else:
            row["respaldo_citas"] = "no se evalúa (C0)"
        row["abstencion_apropiada"] = f"{count(unans, 'abstencion')}/{len(unans)}"
        row["tiempo_medio_s"] = round(sum(float(r["tiempo_total_s"]) for r in rs) / len(rs), 2)
        row["contextos_recortados"] = sum(r["contexto_recortado"] == "1" for r in rs) if is_rag else "no aplica"
        row["valores_pendientes"] = pend
        row["valores_solo_auto"] = auto_used
        table.append(row)

    cols = list(table[0].keys())
    md = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    md += ["| " + " | ".join(str(r[c]) for c in cols) + " |" for r in table]
    note = ("\n\nNotas: cobertura = preguntas respondibles (6) con TODOS los pasajes necesarios completos; "
            "corrección = respuestas correctas y completas sobre 6 (parcial o abstención = incorrecta); "
            "respaldo = respuestas sustantivas cuyas afirmaciones centrales están respaldadas por los pasajes "
            "citados; abstención = preguntas sin respuesta (3) donde el sistema se abstiene sin añadir "
            "contenido sin respaldo. C0 usa instrucciones adaptadas a la ausencia de documentos y sus citas no "
            "se evalúan. 'valores_solo_auto' > 0 indica celdas que aún dependen de la pre-valoración "
            "automática y deben revisarse a mano antes del informe.")
    (run_dir / "tabla_resultados.md").write_text("\n".join(md) + note + "\n", encoding="utf-8")
    with (run_dir / "resultados_metricas.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(table)
    return table
