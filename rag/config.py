"""Configuraciones experimentales (R0, R1, R2, C0 y experimento B).

Todo lo que NO aparece como diferencia entre configuraciones se mantiene fijo:
corpus, preguntas, LLM, temperatura, límite de salida, semilla, plantilla de instrucciones
(R0/R1/R2) y límite máximo de contexto.

Los identificadores de modelos se pueden sobrescribir con variables de entorno
(ver .env.example) sin tocar el código; el valor efectivo queda registrado en cada corrida.
"""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field, replace

# ---------------------------------------------------------------- modelos (registrados)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter")
LLM_MODEL = os.getenv("LLM_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
LLM_MODEL_ALT = os.getenv("LLM_MODEL_ALT", "google/gemma-3-27b-it:free")  # experimento B
EMB_MODEL = os.getenv("EMB_MODEL", "intfloat/multilingual-e5-base")
EMB_MODEL_ALT = os.getenv("EMB_MODEL_ALT", "BAAI/bge-m3")                   # experimento B

# Unidad de "token" para fragmentar y medir el contexto: SIEMPRE el tokenizador del modelo de
# embeddings base, también en el experimento B, para que el corte de fragmentos sea idéntico
# y solo cambie el modelo que los codifica.
CHUNK_TOKENIZER = os.getenv("CHUNK_TOKENIZER", EMB_MODEL)

# Modo de prueba sin red: embeddings por hashing de n-gramas, tokenizador regex y LLM simulado.
# Solo sirve para verificar la tubería; NUNCA para los resultados del informe.
TEST_MODE = os.getenv("RAG_TEST_MODE", "0") == "1"


@dataclass(frozen=True)
class Config:
    name: str
    descripcion: str
    use_rag: bool = True
    # fragmentación
    chunking: str = "fixed"            # "fixed" | "structural"
    chunk_size: int = 400              # tokens
    chunk_overlap: int = 60            # tokens (15 %)
    # recuperación
    retrieval: str = "dense"           # "dense" | "hybrid"
    k: int = 4
    rrf_k: int = 60                    # constante de Reciprocal Rank Fusion (solo híbrida)
    bm25_k1: float = 1.5
    bm25_b: float = 0.75
    # modelos
    embedding_model: str = EMB_MODEL
    chunk_tokenizer: str = CHUNK_TOKENIZER
    llm_provider: str = LLM_PROVIDER
    llm_model: str = LLM_MODEL
    # generación (fijos en todas las configuraciones)
    temperature: float = 0.0
    top_p: float = 1.0
    max_tokens: int = 512              # límite de salida
    seed: int = 42
    max_context_tokens: int = 2400     # límite máximo del contexto con fragmentos (R0/R1/R2):
                                       # 4 x 400 tokens + encabezados de archivo/ubicación
                                       # (~60-100 tokens c/u); k=8 lo supera
    prompt_version: str = "rag-v1"
    test_mode: bool = TEST_MODE
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


R0 = Config(
    name="R0",
    descripcion="Base: fragmentos fijos de 400 tokens con 60 de solapamiento, embeddings densos, "
                "similitud coseno, k=4.",
)

R1 = replace(
    R0, name="R1",
    chunking="structural",
    chunk_overlap=0,
    descripcion="Fragmentación estructural: cortes en límites de párrafo sin cruzar secciones de primer "
                "nivel; se agrupan párrafos completos hasta 400 tokens; sin solapamiento. Un párrafo de más "
                "de 400 tokens se divide con ventana fija 400/60. Todo lo demás igual a R0.",
)

R2 = replace(
    R0, name="R2",
    retrieval="hybrid",
    descripcion="Recuperación híbrida: ranking denso (coseno) + BM25 (k1=1.5, b=0.75) fusionados con "
                "Reciprocal Rank Fusion (constante 60); se conserva k=4. Todo lo demás igual a R0.",
)

C0 = replace(
    R0, name="C0",
    use_rag=False,
    prompt_version="c0-v1",
    descripcion="Control sin recuperación: mismo LLM, mismas preguntas, sin documentos ni fragmentos. "
                "Instrucciones adaptadas: responder con conocimiento propio y señalar si carece de información.",
)

# Experimento B (sobre R0). Se separan los dos cambios para poder atribuir los efectos.
B1 = replace(
    R0, name="B1",
    embedding_model=EMB_MODEL_ALT,
    descripcion=f"R0 con otro modelo de embeddings ({EMB_MODEL_ALT}); índice reconstruido y consultas "
                "codificadas con el nuevo modelo. Fragmentos idénticos a R0.",
)
B2 = replace(
    R0, name="B2",
    llm_model=LLM_MODEL_ALT,
    descripcion=f"R0 con otro LLM ({LLM_MODEL_ALT}). Recuperación idéntica a R0.",
)
B3 = replace(
    R0, name="B3",
    embedding_model=EMB_MODEL_ALT, llm_model=LLM_MODEL_ALT,
    descripcion="R0 con ambos cambios a la vez (embeddings y LLM alternativos).",
)

# Variante opcional (no forma parte de las 36 corridas): R2 alternativa que solo cambia k.
# Con 8 x 400 tokens supera el límite de contexto, así que permite observar el recorte.
R2K8 = replace(R0, name="R2K8", k=8,
               descripcion="Variante opcional: R0 con k=8 (búsqueda densa). Supera el límite de contexto; "
                           "se registra el recorte de fragmentos.")

CONFIGS: dict[str, Config] = {c.name: c for c in (R0, R1, R2, C0, B1, B2, B3, R2K8)}
CONFIGS_PARTE_A = ["R0", "R1", "R2", "C0"]
CONFIGS_PARTE_B = ["B1", "B2", "B3"]


def get_config(name: str) -> Config:
    if name not in CONFIGS:
        raise KeyError(f"Configuración desconocida: {name}. Opciones: {list(CONFIGS)}")
    return CONFIGS[name]
