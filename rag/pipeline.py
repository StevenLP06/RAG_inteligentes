"""Sistema RAG de punta a punta: ingesta -> fragmentación -> índice -> recuperación -> contexto -> LLM -> citas."""
from __future__ import annotations

import re
import time
from pathlib import Path

from . import prompts
from .chunking import chunk_corpus, get_token_counter
from .config import Config
from .ingest import corpus_summary, load_corpus
from .llm import LLMClient
from .retrieval import Retriever, get_embedder

CITE_RE = re.compile(r"\[(F\d+)\]")


def detect_abstention(text: str) -> dict:
    """Clasifica la respuesta: abstención total, parcial (declara parte no cubierta) o sustantiva."""
    t = text.strip()
    up = t.upper()
    starts = up.startswith(prompts.ABSTAIN_RAG.upper().rstrip(":")) or \
        up.startswith(prompts.ABSTAIN_C0.upper().rstrip(":"))
    mentions = (prompts.ABSTAIN_RAG.upper().rstrip(":") in up) or (prompts.ABSTAIN_C0.upper().rstrip(":") in up) \
        or bool(re.search(r"no (est[aá]|se encuentra|aparece|figura) (cubiert|en los (documentos|fragmentos))", t, re.I))
    if starts:
        return {"abstencion": True, "tipo": "total"}
    if mentions:
        return {"abstencion": False, "tipo": "parcial"}
    return {"abstencion": False, "tipo": "sustantiva"}


class RAGSystem:
    def __init__(self, cfg: Config, corpus_dir: str | Path):
        self.cfg = cfg
        self.corpus_dir = Path(corpus_dir)
        self.llm = LLMClient(cfg.llm_provider, cfg.llm_model, cfg.temperature, cfg.max_tokens, cfg.seed,
                             cfg.top_p, test_mode=cfg.test_mode)
        self.chunks = []
        self.retriever = None
        self.build_info: dict = {}
        if cfg.use_rag:
            self.build()

    # ------------------------------------------------------------------------ indexación
    def build(self):
        t0 = time.perf_counter()
        self.units = load_corpus(self.corpus_dir)
        self.tc = get_token_counter(self.cfg.chunk_tokenizer, self.cfg.test_mode)
        self.chunks = chunk_corpus(self.units, self.cfg, self.tc)
        embedder = get_embedder(self.cfg.embedding_model, self.cfg.test_mode)
        self.retriever = Retriever(self.chunks, embedder, self.cfg)
        self.build_info = {
            "corpus": corpus_summary(self.units),
            "n_fragmentos": len(self.chunks),
            "tokens_por_fragmento": {"min": min(c.n_tokens for c in self.chunks),
                                     "max": max(c.n_tokens for c in self.chunks),
                                     "media": round(sum(c.n_tokens for c in self.chunks) / len(self.chunks), 1)},
            "tokenizador": self.tc.name,
            "embeddings": embedder.name,
            "prefijos_embeddings": {"consulta": embedder.q_prefix, "documento": embedder.d_prefix},
            "tiempo_indexacion_s": round(time.perf_counter() - t0, 2),
        }
        return self.build_info

    # ------------------------------------------------------------------------ contexto
    def build_context(self, retrieved: list[dict]) -> tuple[str, list[dict], bool]:
        """Arma el contexto respetando max_context_tokens. Registra si hubo recorte."""
        budget = self.cfg.max_context_tokens
        used = 0
        blocks, estado = [], []
        truncated = False
        for i, item in enumerate(retrieved, start=1):
            label = f"F{i}"
            full_block = prompts.format_fragment(label, item, item["chunk"].text)
            n = self.tc.count(full_block)
            if used + n <= budget:
                blocks.append(full_block)
                used += n
                estado.append({"etiqueta": label, "chunk_id": item["chunk"].chunk_id, "estado": "completo",
                               "tokens": n, "texto_enviado": item["chunk"].text})
                continue
            truncated = True
            header = prompts.format_fragment(label, item, "")
            room = budget - used - self.tc.count(header) - 8  # margen para " […]" y separadores
            if room >= 40:  # se incluye recortado si cabe una porción útil
                txt = self.tc.truncate(item["chunk"].text, room) + " […]"
                blk = prompts.format_fragment(label, item, txt)
                blocks.append(blk)
                used += self.tc.count(blk)
                estado.append({"etiqueta": label, "chunk_id": item["chunk"].chunk_id, "estado": "recortado",
                               "tokens": self.tc.count(blk), "texto_enviado": txt})
            else:
                estado.append({"etiqueta": label, "chunk_id": item["chunk"].chunk_id, "estado": "omitido",
                               "tokens": 0, "texto_enviado": ""})
        return "\n\n".join(blocks), estado, truncated

    # ------------------------------------------------------------------------ consulta
    def ask(self, question: str) -> dict:
        t0 = time.perf_counter()
        out: dict = {"pregunta": question, "configuracion": self.cfg.name}
        if not self.cfg.use_rag:
            system, user = prompts.SYSTEM_C0, prompts.USER_C0.format(pregunta=question)
            t_ret = 0.0
            out.update({"recuperados": [], "contexto": None, "contexto_estado": [], "contexto_recortado": None})
        else:
            tr = time.perf_counter()
            retrieved = self.retriever.search(question)
            t_ret = time.perf_counter() - tr
            context, estado, truncated = self.build_context(retrieved)
            system = prompts.SYSTEM_RAG
            user = prompts.USER_RAG.format(contexto=context, pregunta=question)
            out.update({
                "recuperados": [{"rank": it["rank"], "etiqueta": f"F{it['rank']}", **it["chunk"].to_dict(),
                                 **{k: round(v, 5) if isinstance(v, float) else v for k, v in it.items()
                                    if k not in ("chunk", "rank")}} for it in retrieved],
                "contexto": context, "contexto_estado": estado, "contexto_recortado": truncated,
                "tokens_contexto": self.tc.count(context),
            })
        resp = self.llm.chat(system, user)
        answer = resp["texto"]
        out.update({
            "respuesta": answer,
            "modelo_llm": self.cfg.llm_model, "modelo_servido": resp.get("modelo_servido"),
            "proveedor_servido": resp.get("proveedor_servido"), "uso_tokens": resp.get("uso"),
            "intentos_llm": resp.get("intentos"),
            **detect_abstention(answer),
        })
        out["citas"] = self.resolve_citations(answer, out.get("recuperados", []))
        out["tiempo_recuperacion_s"] = round(t_ret, 4)
        out["tiempo_llm_s"] = round(resp.get("latencia_s", 0.0), 3)
        out["tiempo_total_s"] = round(time.perf_counter() - t0, 3)
        out["prompt_system"] = system
        out["prompt_user"] = user
        return out

    @staticmethod
    def resolve_citations(answer: str, recuperados: list[dict]) -> list[dict]:
        by_label = {r["etiqueta"]: r for r in recuperados}
        citas, seen = [], set()
        for lab in CITE_RE.findall(answer):
            if lab in seen:
                continue
            seen.add(lab)
            r = by_label.get(lab)
            citas.append({"etiqueta": lab, "valida": r is not None,
                          "archivo": r["archivo"] if r else None,
                          "localizador": r["localizador"] if r else None,
                          "chunk_id": r["chunk_id"] if r else None})
        return citas


def format_result(res: dict, show_text_chars: int = 400) -> str:
    """Representación legible: respuesta, fragmentos recuperados en orden y citas."""
    L = [f"Configuración: {res['configuracion']}", f"Pregunta: {res['pregunta']}", "",
         "RESPUESTA:", res["respuesta"], ""]
    if res.get("abstencion"):
        L.append("⚠ El sistema indica que la evidencia es insuficiente.\n")
    if res.get("recuperados"):
        L.append("FRAGMENTOS RECUPERADOS (en orden):")
        estado = {e["etiqueta"]: e["estado"] for e in res.get("contexto_estado", [])}
        for r in res["recuperados"]:
            extra = f" | denso={r.get('score_denso')}" + (f" bm25={r['score_bm25']}" if "score_bm25" in r else "")
            L.append(f"  [{r['etiqueta']}] score={r['score']}{extra} | {r['archivo']} | {r['localizador']} "
                     f"| contexto: {estado.get(r['etiqueta'], '-')}")
            t = r["texto"].replace("\n", " ")
            L.append("       " + (t[:show_text_chars] + ("…" if len(t) > show_text_chars else "")))
        L.append("")
        L.append("CITAS:")
        if not res["citas"]:
            L.append("  (la respuesta no contiene citas)")
        for c in res["citas"]:
            L.append(f"  [{c['etiqueta']}] -> {c['archivo']} · {c['localizador']}" if c["valida"]
                     else f"  [{c['etiqueta']}] -> ⚠ cita inválida (no corresponde a un fragmento recuperado)")
        if res.get("contexto_recortado"):
            L.append("\n⚠ El límite de contexto obligó a recortar u omitir fragmentos.")
    L.append(f"\nTiempo total: {res['tiempo_total_s']} s (recuperación {res['tiempo_recuperacion_s']} s, "
             f"LLM {res['tiempo_llm_s']} s) · modelo servido: {res.get('modelo_servido')}")
    return "\n".join(L)
