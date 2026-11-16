"""API HTTP para la interfaz web del asistente RAG.

Capa delgada sobre ``rag.pipeline.RAGSystem``: no modifica la lógica del sistema, solo la expone.

    uvicorn api.server:app --port 8000              # desarrollo (la web corre con `npm run dev`)
    uvicorn api.server:app --port 8000              # producción: sirve también web/dist si existe

Cada configuración (R0, R1, ...) se construye una sola vez (ingesta + índice) y se reutiliza.
"""
from __future__ import annotations

import json
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")  # antes de importar rag.config, que lee las variables al cargarse

from rag.config import CONFIGS, CONFIGS_PARTE_A, CONFIGS_PARTE_B, get_config  # noqa: E402
from rag.ingest import SUPPORTED  # noqa: E402
from rag.llm import LLMError  # noqa: E402
from rag.pipeline import RAGSystem  # noqa: E402

CORPUS_DIR = ROOT / "corpus"
QUESTIONS_PATH = ROOT / "evaluacion" / "preguntas.json"
WEB_DIST = ROOT / "web" / "dist"
DEFAULT_CONFIG = "R0"

# Campos de la respuesta del pipeline que no se envían al navegador (prompts completos y contexto
# concatenado: son voluminosos y el detalle por fragmento ya va en "recuperados"/"contexto_estado").
_OMIT = {"prompt_system", "prompt_user", "contexto"}


# ------------------------------------------------------------------ caché de sistemas
class SystemPool:
    """Construye cada RAGSystem de forma perezosa y una sola vez, aun con peticiones concurrentes."""

    def __init__(self):
        self._systems: dict[str, RAGSystem] = {}
        self._build_locks: dict[str, threading.Lock] = {name: threading.Lock() for name in CONFIGS}
        self._ask_locks: dict[str, threading.Lock] = {name: threading.Lock() for name in CONFIGS}
        self.errors: dict[str, str] = {}

    def ready(self, name: str) -> bool:
        return name in self._systems

    def get(self, name: str) -> RAGSystem:
        if name in self._systems:
            return self._systems[name]
        with self._build_locks[name]:
            if name not in self._systems:
                try:
                    self._systems[name] = RAGSystem(get_config(name), CORPUS_DIR)
                    self.errors.pop(name, None)
                except Exception as e:  # se informa al cliente y se reintenta en la próxima petición
                    self.errors[name] = f"{type(e).__name__}: {e}"
                    raise
        return self._systems[name]

    def ask(self, name: str, question: str) -> dict:
        system = self.get(name)
        # Los modelos de embeddings no garantizan seguridad entre hilos: una consulta por config a la vez.
        with self._ask_locks[name]:
            return system.ask(question)


pool = SystemPool()


# ------------------------------------------------------------------ app
@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Precalienta la configuración por defecto en segundo plano (carga de embeddings e índice),
    # para que la primera pregunta no espere la indexación.
    def run():
        try:
            pool.get(DEFAULT_CONFIG)
        except Exception:
            pass  # el error queda en pool.errors y se reporta en /api/health
    threading.Thread(target=run, daemon=True).start()
    yield


app = FastAPI(title="RAG Mesa de Ayuda — API", version="1.0", lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["GET", "POST"], allow_headers=["*"])


class AskBody(BaseModel):
    pregunta: str = Field(min_length=2, max_length=2000)
    config: str = DEFAULT_CONFIG


@app.get("/api/health")
def health():
    return {"ok": True, "listas": [n for n in CONFIGS if pool.ready(n)], "errores": pool.errors}


@app.get("/api/info")
def info():
    configs = [{"nombre": c.name, "descripcion": c.descripcion, "usa_rag": c.use_rag,
                "recuperacion": c.retrieval if c.use_rag else None,
                "fragmentacion": c.chunking if c.use_rag else None, "k": c.k if c.use_rag else None,
                "llm": c.llm_model, "embeddings": c.embedding_model if c.use_rag else None,
                "grupo": "A" if c.name in CONFIGS_PARTE_A else "B" if c.name in CONFIGS_PARTE_B else "extra",
                "lista": pool.ready(c.name)} for c in CONFIGS.values()]
    corpus = [{"archivo": f.name, "formato": f.suffix.lstrip(".").lower(), "bytes": f.stat().st_size}
              for f in sorted(CORPUS_DIR.iterdir()) if f.suffix.lower() in SUPPORTED]
    sugerencias = []
    if QUESTIONS_PATH.exists():
        data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
        sugerencias = [q["pregunta"] for q in data.get("preguntas", [])]
    return {"configuraciones": configs, "por_defecto": DEFAULT_CONFIG, "corpus": corpus,
            "sugerencias": sugerencias}


@app.post("/api/ask")
def ask(body: AskBody):
    # Función síncrona: FastAPI la ejecuta en un hilo y no bloquea el bucle de eventos.
    if body.config not in CONFIGS:
        raise HTTPException(400, f"Configuración desconocida: {body.config}")
    try:
        res = pool.ask(body.config, body.pregunta.strip())
    except LLMError as e:
        raise HTTPException(502, f"El modelo de lenguaje no respondió: {e}") from e
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}") from e
    return {k: v for k, v in res.items() if k not in _OMIT}


@app.get("/api/corpus/{archivo}")
def corpus_file(archivo: str):
    path = (CORPUS_DIR / archivo).resolve()
    if path.parent != CORPUS_DIR.resolve() or not path.is_file() or path.suffix.lower() not in SUPPORTED:
        raise HTTPException(404, "Documento no encontrado")
    return FileResponse(path, filename=path.name, content_disposition_type="inline")


# ------------------------------------------------------------------ interfaz compilada (opcional)
if WEB_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = (WEB_DIST / path).resolve()
        if path and f.is_file() and WEB_DIST.resolve() in f.parents:
            return FileResponse(f)
        return FileResponse(WEB_DIST / "index.html", headers={"Cache-Control": "no-cache"})
