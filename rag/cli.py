"""Interfaz de línea de comandos.

  python -m rag.cli preguntar "¿Qué hago con el error VPN-809?" --config R0
  python -m rag.cli fragmentos --config R1            # inspecciona fragmentos y localizadores
  python -m rag.cli evaluar --configs R0 R1 R2 C0 --salida resultados/parte_A
  python -m rag.cli metricas --salida resultados/parte_A
"""
from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def main():
    load_dotenv(ROOT / ".env")
    from .config import CONFIGS_PARTE_A, get_config
    from .evaluation import compute_metrics, export_valoracion, run_evaluation
    from .pipeline import RAGSystem, format_result

    ap = argparse.ArgumentParser(description="RAG Mesa de Ayuda TI (Andina Tech, ficticia)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("preguntar"); p.add_argument("pregunta"); p.add_argument("--config", default="R0")
    f = sub.add_parser("fragmentos"); f.add_argument("--config", default="R0")
    e = sub.add_parser("evaluar"); e.add_argument("--configs", nargs="+", default=CONFIGS_PARTE_A)
    e.add_argument("--salida", default="resultados/parte_A")
    m = sub.add_parser("metricas"); m.add_argument("--salida", default="resultados/parte_A")
    for s in (p, f, e):
        s.add_argument("--corpus", default=str(ROOT / "corpus"))
    a = ap.parse_args()

    if a.cmd == "preguntar":
        print(format_result(RAGSystem(get_config(a.config), a.corpus).ask(a.pregunta)))
    elif a.cmd == "fragmentos":
        s = RAGSystem(get_config(a.config), a.corpus)
        print(s.build_info)
        for c in s.chunks:
            print(f"{c.chunk_id:42s} {c.n_tokens:4d} tok | {c.locator}")
    elif a.cmd == "evaluar":
        run_evaluation(a.configs, ROOT / "evaluacion" / "preguntas.json", a.corpus, a.salida)
        export_valoracion(a.salida)
        for r in compute_metrics(a.salida):
            print(r)
    elif a.cmd == "metricas":
        export_valoracion(a.salida)
        for r in compute_metrics(a.salida):
            print(r)


if __name__ == "__main__":
    main()
