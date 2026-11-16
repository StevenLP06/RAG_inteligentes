"""Embeddings, índice denso (coseno), BM25 y búsqueda híbrida (RRF)."""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from functools import lru_cache

import numpy as np

from .chunking import Chunk


# ------------------------------------------------------------------------- embeddings
# Prefijos que exigen algunos modelos (mismo modelo para documentos y consultas).
PREFIXES = {
    "intfloat/multilingual-e5": ("query: ", "passage: "),
    "intfloat/e5": ("query: ", "passage: "),
}


def _prefixes(model_name: str) -> tuple[str, str]:
    for key, val in PREFIXES.items():
        if model_name.startswith(key):
            return val
    return ("", "")


class Embedder:
    def __init__(self, model_name: str, test_mode: bool = False):
        self.model_name = model_name
        self.test_mode = test_mode
        self.q_prefix, self.d_prefix = _prefixes(model_name)
        if test_mode:
            from sklearn.feature_extraction.text import HashingVectorizer
            self._vec = HashingVectorizer(analyzer="char_wb", ngram_range=(3, 5), n_features=2 ** 16,
                                          alternate_sign=False, norm="l2")
            self.name = "test-hash-char-ngrams (SOLO PRUEBAS)"
        else:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(model_name)
            self.name = model_name

    def _encode(self, texts: list[str]) -> np.ndarray:
        if self.test_mode:
            return self._vec.transform(texts).toarray().astype(np.float32)
        emb = self._model.encode(texts, normalize_embeddings=True, batch_size=16,
                                 show_progress_bar=False, convert_to_numpy=True)
        return emb.astype(np.float32)

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        return self._encode([self.d_prefix + t for t in texts])

    def embed_query(self, text: str) -> np.ndarray:
        return self._encode([self.q_prefix + text])[0]


@lru_cache(maxsize=4)
def get_embedder(model_name: str, test_mode: bool) -> Embedder:
    return Embedder(model_name, test_mode)


# ------------------------------------------------------------------------- índice denso
class DenseIndex:
    def __init__(self, chunks: list[Chunk], embedder: Embedder):
        self.chunks = chunks
        self.embedder = embedder
        m = embedder.embed_documents([c.text for c in chunks])
        norms = np.linalg.norm(m, axis=1, keepdims=True)
        self.matrix = m / np.clip(norms, 1e-12, None)

    def scores(self, query: str) -> np.ndarray:
        q = self.embedder.embed_query(query)
        q = q / max(np.linalg.norm(q), 1e-12)
        return self.matrix @ q  # similitud coseno


# ------------------------------------------------------------------------- BM25
_STOP = set("""a al algo ante con contra cual cuales cuando de del desde donde e el ella ellas ellos en entre
era es esa ese eso esta este esto estos estas fue ha hay la las le les lo los mas me mi mis muy ni no nos o
os otra otro para pero por porque que se si sin sobre su sus te tiene tu un una uno unos unas y ya yo como
debo puedo cuanto cuanta cuantos cuantas hacer qué cómo cuál""".split())


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


_STOP = {normalize(w) for w in _STOP}


def bm25_tokens(text: str) -> list[str]:
    # conserva códigos como "vpn-809" o "550" como términos
    toks = re.findall(r"[a-z0-9]+(?:[-.][a-z0-9]+)*", normalize(text))
    return [t for t in toks if t not in _STOP and len(t) > 1]


class BM25:
    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = [Counter(bm25_tokens(c.text)) for c in chunks]
        self.lens = np.array([sum(d.values()) for d in self.docs], dtype=float)
        self.avgdl = float(self.lens.mean()) if len(self.lens) else 0.0
        n = len(self.docs)
        df = Counter()
        for d in self.docs:
            df.update(d.keys())
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def scores(self, query: str) -> np.ndarray:
        q = bm25_tokens(query)
        out = np.zeros(len(self.docs))
        for i, d in enumerate(self.docs):
            s = 0.0
            for t in q:
                if t in d:
                    tf = d[t]
                    s += self.idf[t] * tf * (self.k1 + 1) / (
                        tf + self.k1 * (1 - self.b + self.b * self.lens[i] / self.avgdl))
            out[i] = s
        return out


# ------------------------------------------------------------------------- recuperador
def _ranks(scores: np.ndarray) -> np.ndarray:
    order = np.argsort(-scores, kind="stable")
    r = np.empty(len(scores), dtype=int)
    r[order] = np.arange(1, len(scores) + 1)
    return r


class Retriever:
    def __init__(self, chunks: list[Chunk], embedder: Embedder, cfg):
        self.cfg = cfg
        self.chunks = chunks
        self.dense = DenseIndex(chunks, embedder)
        self.bm25 = BM25(chunks, cfg.bm25_k1, cfg.bm25_b) if cfg.retrieval == "hybrid" else None

    def search(self, query: str) -> list[dict]:
        k = self.cfg.k
        dense = self.dense.scores(query)
        if self.cfg.retrieval == "dense":
            order = np.argsort(-dense, kind="stable")[:k]
            return [{"rank": r + 1, "chunk": self.chunks[i], "score": float(dense[i]),
                     "score_denso": float(dense[i])} for r, i in enumerate(order)]
        # híbrida: Reciprocal Rank Fusion sobre los rankings completos (corpus pequeño)
        sparse = self.bm25.scores(query)
        rd, rs = _ranks(dense), _ranks(sparse)
        fused = 1.0 / (self.cfg.rrf_k + rd) + 1.0 / (self.cfg.rrf_k + rs)
        order = np.argsort(-fused, kind="stable")[:k]
        return [{"rank": r + 1, "chunk": self.chunks[i], "score": float(fused[i]),
                 "score_denso": float(dense[i]), "rank_denso": int(rd[i]),
                 "score_bm25": float(sparse[i]), "rank_bm25": int(rs[i])} for r, i in enumerate(order)]
