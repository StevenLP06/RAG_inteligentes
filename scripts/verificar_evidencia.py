"""Verifica que cada pasaje de evidencia del conjunto de evaluación exista literalmente en el corpus
e imprime su ubicación real (página/líneas, sección/párrafo). Ejecutar antes de las corridas finales.

Uso: python scripts/verificar_evidencia.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rag.evaluation import load_questions, norm  # noqa: E402
from rag.ingest import load_corpus  # noqa: E402


def main() -> int:
    units = load_corpus(ROOT / "corpus")
    by_doc: dict[str, list] = {}
    for u in units:
        by_doc.setdefault(u.doc, []).append(u)
    errores = 0
    for q in load_questions(ROOT / "evaluacion" / "preguntas.json"):
        print(f"{q['id']} ({q['tipo']}): {q['pregunta']}")
        if not q["evidencia"]:
            print(f"   sin evidencia esperada -> {q.get('justificacion', '')[:110]}…")
        for ev in q["evidencia"]:
            n = norm(ev["texto"])
            hits = [u for u in by_doc.get(ev["archivo"], []) if n in norm(u.text)]
            if not hits:
                # el pasaje puede abarcar dos unidades consecutivas
                us = by_doc.get(ev["archivo"], [])
                hits = [a for a, b in zip(us, us[1:]) if n in norm(a.text + " " + b.text)]
            if hits:
                u = hits[0]
                loc = (f"pág. {u.page}, línea {u.line_start}" if u.fmt == "pdf" else
                    f"§ {u.section}, ¶{u.para}" if u.fmt == "docx" else f"línea {u.line_start}")
                print(f"   OK  {ev['archivo']} · {loc} · sección: {u.heading_path}")
            else:
                errores += 1
                print(f"   ERROR: no se encontró en {ev['archivo']}: {ev['texto'][:80]}…")
    print("\nTodas las evidencias verificadas." if not errores else f"\n{errores} evidencias NO encontradas.")
    return 1 if errores else 0


if __name__ == "__main__":
    raise SystemExit(main())
