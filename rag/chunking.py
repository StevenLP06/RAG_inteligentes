"""Tokenización y fragmentación.

- fixed_chunks: ventana fija de N tokens con solapamiento (R0, R2, B*). No cruza documentos.
- structural_chunks: agrupa párrafos completos de una misma sección hasta N tokens (R1).

Cada fragmento conserva el archivo y un localizador verificable calculado a partir de las
unidades (y de los desplazamientos de caracteres) que cubre.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache

from .ingest import Unit


# ------------------------------------------------------------------------- tokenizador
class TokenCounter:
    """Cuenta tokens y devuelve desplazamientos (offsets) de caracteres por token."""

    def __init__(self, model_name: str, test_mode: bool = False):
        self.model_name = model_name
        self._tok = None
        if not test_mode:
            from transformers import AutoTokenizer  # requiere red la primera vez
            self._tok = AutoTokenizer.from_pretrained(model_name, use_fast=True)
            self.name = f"hf:{model_name}"
        else:
            self.name = "regex-fallback (SOLO PRUEBAS)"

    def offsets(self, text: str) -> list[tuple[int, int]]:
        if self._tok is None:
            return [(m.start(), m.end()) for m in re.finditer(r"\w+|[^\w\s]", text)]
        enc = self._tok(text, add_special_tokens=False, return_offsets_mapping=True)
        return [tuple(o) for o in enc["offset_mapping"] if o[1] > o[0]]

    def count(self, text: str) -> int:
        return len(self.offsets(text))

    def truncate(self, text: str, n: int) -> str:
        offs = self.offsets(text)
        if len(offs) <= n:
            return text
        return text[: offs[n - 1][1]] if n > 0 else ""


@lru_cache(maxsize=4)
def get_token_counter(model_name: str, test_mode: bool) -> TokenCounter:
    return TokenCounter(model_name, test_mode)


# ------------------------------------------------------------------------- fragmento
@dataclass
class Piece:
    """Porción [start, end) del texto de una unidad incluida en un fragmento."""
    unit: Unit
    start: int
    end: int


@dataclass
class Chunk:
    chunk_id: str
    doc: str
    fmt: str
    text: str
    n_tokens: int
    locator: str
    pieces: list[Piece] = field(repr=False, default_factory=list)
    order: int = 0  # posición dentro del documento

    def to_dict(self) -> dict:
        return {"chunk_id": self.chunk_id, "archivo": self.doc, "formato": self.fmt,
                "localizador": self.locator, "n_tokens": self.n_tokens, "texto": self.text}


def _rng(a, b, sep="–"):
    return f"{a}" if a == b else f"{a}{sep}{b}"


def make_locator(pieces: list[Piece]) -> str:
    fmt = pieces[0].unit.fmt
    if fmt == "pdf":
        by_page: dict[int, list[int]] = {}
        secs: list[str] = []
        for p in pieces:
            u = p.unit
            l1, l2 = u.line_at(p.start), u.line_at(max(p.end - 1, p.start))
            by_page.setdefault(u.page, []).extend([l1, l2])
            if u.section not in secs:
                secs.append(u.section)
        parts = [f"pág. {pg}, líneas {_rng(min(ls), max(ls))}" for pg, ls in by_page.items()]
        return "; ".join(parts) + f" (sección: {' | '.join(secs)})"
    if fmt == "docx":
        by_sec: dict[str, list[int]] = {}
        glob = []
        for p in pieces:
            u = p.unit
            by_sec.setdefault(u.section, []).append(u.para or 0)
            glob.append(u.para_global)
        parts = []
        for sec, ps in by_sec.items():
            body = [x for x in ps if x > 0]
            parts.append(f"§ «{sec}», ¶{_rng(min(body), max(body))}" if body else f"§ «{sec}» (título)")
        return "; ".join(parts) + f" [párrafos globales {_rng(min(glob), max(glob))}]"
    # md / txt
    l1 = pieces[0].unit.line_at(pieces[0].start)
    last = pieces[-1]
    l2 = last.unit.line_at(max(last.end - 1, last.start))
    secs: list[str] = []
    for p in pieces:
        if p.unit.heading_path not in secs:
            secs.append(p.unit.heading_path)
    sec_txt = secs[0] if len(secs) == 1 else f"{secs[0]} … {secs[-1]}"
    return f"líneas {_rng(l1, l2)} (sección: {sec_txt})"


def _build_chunk(doc_units: list[Unit], pieces: list[Piece], tc: TokenCounter, idx: int) -> Chunk:
    text = "\n\n".join(p.unit.text[p.start:p.end].strip() for p in pieces).strip()
    u0 = pieces[0].unit
    return Chunk(chunk_id=f"{u0.doc}#{idx:03d}", doc=u0.doc, fmt=u0.fmt, text=text,
                 n_tokens=tc.count(text), locator=make_locator(pieces), pieces=pieces, order=idx)


def _group_by_doc(units: list[Unit]) -> dict[str, list[Unit]]:
    docs: dict[str, list[Unit]] = {}
    for u in units:
        docs.setdefault(u.doc, []).append(u)
    return docs


def _window_over_units(units: list[Unit], size: int, overlap: int, tc: TokenCounter) -> list[list[Piece]]:
    """Ventana deslizante sobre el flujo de tokens de una secuencia de unidades."""
    stream: list[tuple[int, int, int]] = []  # (idx unidad, ini, fin)
    for ui, u in enumerate(units):
        for s, e in tc.offsets(u.text):
            stream.append((ui, s, e))
    if not stream:
        return []
    step = size - overlap
    assert step > 0, "el solapamiento debe ser menor que el tamaño"
    windows = []
    start = 0
    while True:
        end = min(start + size, len(stream))
        toks = stream[start:end]
        pieces: list[Piece] = []
        for ui, s, e in toks:
            if pieces and pieces[-1].unit is units[ui]:
                pieces[-1].end = e
            else:
                pieces.append(Piece(units[ui], s, e))
        windows.append(pieces)
        if end >= len(stream):
            break
        start += step
    return windows


def fixed_chunks(units: list[Unit], size: int, overlap: int, tc: TokenCounter) -> list[Chunk]:
    chunks: list[Chunk] = []
    for doc, us in _group_by_doc(units).items():
        for i, pieces in enumerate(_window_over_units(us, size, overlap, tc)):
            chunks.append(_build_chunk(us, pieces, tc, i))
    return chunks


def structural_chunks(units: list[Unit], max_tokens: int, tc: TokenCounter,
                      long_overlap: int = 60) -> list[Chunk]:
    """Regla R1: cortes solo en límites de párrafo; nunca se cruza una sección de primer nivel;
    se agrupan párrafos completos mientras el total no supere max_tokens; sin solapamiento.
    Un párrafo que por sí solo supera max_tokens se divide con ventana fija (max_tokens/long_overlap)."""
    chunks: list[Chunk] = []
    for doc, us in _group_by_doc(units).items():
        groups: list[list[Piece]] = []
        cur: list[Piece] = []
        cur_tok = 0
        cur_sec = None
        for u in us:
            n = tc.count(u.text)
            if cur and (u.section != cur_sec or cur_tok + n > max_tokens):
                carry = []
                # un título no debe quedar separado del párrafo que introduce
                while cur and cur[-1].unit.is_heading and u.section == cur_sec:
                    carry.insert(0, cur.pop())
                if cur:
                    groups.append(cur)
                cur = carry
                cur_tok = sum(tc.count(p.unit.text) for p in carry)
            cur_sec = u.section
            if n > max_tokens:  # párrafo excesivamente largo
                if cur:
                    groups.append(cur)
                    cur, cur_tok = [], 0
                groups.extend(_window_over_units([u], max_tokens, long_overlap, tc))
                continue
            cur.append(Piece(u, 0, len(u.text)))
            cur_tok += n
        if cur:
            groups.append(cur)
        # un grupo formado solo por un título se fusiona con el siguiente si cabe
        merged: list[list[Piece]] = []
        for g in groups:
            if merged and all(p.unit.is_heading for p in merged[-1]) \
                    and merged[-1][0].unit.section == g[0].unit.section:
                merged[-1] = merged[-1] + g
            else:
                merged.append(g)
        for i, g in enumerate(merged):
            chunks.append(_build_chunk(us, g, tc, i))
    return chunks


def chunk_corpus(units: list[Unit], cfg, tc: TokenCounter) -> list[Chunk]:
    if cfg.chunking == "fixed":
        return fixed_chunks(units, cfg.chunk_size, cfg.chunk_overlap, tc)
    if cfg.chunking == "structural":
        return structural_chunks(units, cfg.chunk_size, tc)
    raise ValueError(cfg.chunking)
