"""Ingesta: lee PDF, DOCX y MD de una carpeta y los convierte en "unidades" (párrafos/bloques)
que conservan el archivo de origen y un localizador verificable.

Localizadores por formato
  PDF  -> página + líneas del texto extraído de esa página (y la sección detectada)
  DOCX -> sección (título) + número de párrafo dentro de la sección (y número global)
  MD   -> ruta de encabezados + líneas del archivo fuente
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

SUPPORTED = {".pdf", ".docx", ".md", ".markdown", ".txt"}


@dataclass
class Unit:
    doc: str                    # nombre del archivo
    fmt: str                    # pdf | docx | md
    text: str
    order: int                  # posición dentro del documento
    section: str = ""           # sección de primer nivel (para fragmentación estructural)
    heading_path: str = ""      # ruta completa de encabezados (MD/DOCX) o sección (PDF)
    is_heading: bool = False
    page: int | None = None     # PDF
    line_start: int | None = None  # PDF (línea en la página) / MD (línea en el archivo)
    para: int | None = None     # DOCX: párrafo dentro de la sección
    para_global: int | None = None  # DOCX: párrafo en el documento
    meta: dict = field(default_factory=dict)

    def line_at(self, char_offset: int) -> int | None:
        """Línea correspondiente a un desplazamiento de caracteres dentro del texto de la unidad."""
        if self.line_start is None:
            return None
        return self.line_start + self.text[:char_offset].count("\n")


# ------------------------------------------------------------------------------- PDF
_PDF_HEADING = re.compile(r"^\d+(\.\d+)*\.?\s+[A-ZÁÉÍÓÚÑ]")


def load_pdf(path: Path) -> list[Unit]:
    from pypdf import PdfReader

    units: list[Unit] = []
    section = ""
    order = 0
    reader = PdfReader(str(path))
    for pno, page in enumerate(reader.pages, start=1):
        raw = page.extract_text() or ""
        lines = [ln.rstrip() for ln in raw.splitlines()]
        maxlen = max((len(ln) for ln in lines if ln.strip()), default=1)
        buf: list[str] = []
        buf_start = None

        def flush():
            nonlocal buf, buf_start, order
            if buf:
                txt = "\n".join(buf).strip()
                if txt:
                    units.append(Unit(doc=path.name, fmt="pdf", text=txt, order=order, section=section,
                                      heading_path=section, page=pno, line_start=buf_start))
                    order += 1
            buf, buf_start = [], None

        for i, ln in enumerate(lines, start=1):
            if not ln.strip():
                flush()
                continue
            is_head = bool(_PDF_HEADING.match(ln.strip())) and len(ln) < 70 and not ln.strip().endswith(".")
            if is_head:
                flush()
                section = ln.strip()
                units.append(Unit(doc=path.name, fmt="pdf", text=ln.strip(), order=order, section=section,
                                  heading_path=section, is_heading=True, page=pno, line_start=i))
                order += 1
                continue
            if buf_start is None:
                buf_start = i
            buf.append(ln)
            # fin de párrafo: línea notablemente más corta que el ancho de la página
            if len(ln) < 0.8 * maxlen:
                flush()
        flush()
    # El primer bloque antes de cualquier encabezado (título/aviso) queda con sección "(inicio)"
    for u in units:
        if not u.section:
            u.section = u.heading_path = "(inicio)"
    return units


# ------------------------------------------------------------------------------ DOCX
def load_docx(path: Path) -> list[Unit]:
    import docx

    d = docx.Document(str(path))
    units: list[Unit] = []
    section, heading_path = "(inicio)", "(inicio)"
    para_in_sec = 0
    para_global = 0
    order = 0
    for p in d.paragraphs:
        txt = p.text.strip()
        if not txt:
            continue
        style = (p.style.name or "").lower()
        para_global += 1
        if style.startswith("heading") or style == "title":
            level = 0 if style == "title" else int(re.sub(r"\D", "", style) or 1)
            if level <= 1:
                section = heading_path = txt
            else:
                heading_path = f"{section} > {txt}"
            para_in_sec = 0
            units.append(Unit(doc=path.name, fmt="docx", text=txt, order=order, section=section,
                              heading_path=heading_path, is_heading=True, para=0, para_global=para_global))
        else:
            para_in_sec += 1
            units.append(Unit(doc=path.name, fmt="docx", text=txt, order=order, section=section,
                              heading_path=heading_path, para=para_in_sec, para_global=para_global))
        order += 1
    return units


# -------------------------------------------------------------------------------- MD
_MD_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")


def load_md(path: Path) -> list[Unit]:
    lines = path.read_text(encoding="utf-8").splitlines()
    units: list[Unit] = []
    stack: list[tuple[int, str]] = []   # (nivel, título)
    order = 0
    buf: list[str] = []
    buf_start = None

    def top_section() -> str:
        # sección de primer nivel = encabezado de nivel 2 vigente (el H1 es el título del documento)
        for lvl, t in stack:
            if lvl == 2:
                return t
        return stack[0][1] if stack else "(inicio)"

    def path_str() -> str:
        # se omite el H1 (título del documento) para que el localizador sea legible
        inner = [t for l, t in stack if l > 1]
        return " > ".join(inner) or (stack[0][1] if stack else "(inicio)")

    def flush():
        nonlocal buf, buf_start, order
        if buf:
            txt = "\n".join(buf).strip()
            if txt:
                units.append(Unit(doc=path.name, fmt="md", text=txt, order=order, section=top_section(),
                                  heading_path=path_str(), line_start=buf_start))
                order += 1
        buf, buf_start = [], None

    for i, ln in enumerate(lines, start=1):
        m = _MD_HEADING.match(ln)
        if m:
            flush()
            lvl, title = len(m.group(1)), m.group(2).strip()
            stack[:] = [(l, t) for l, t in stack if l < lvl] + [(lvl, title)]
            units.append(Unit(doc=path.name, fmt="md", text=title, order=order, section=top_section(),
                              heading_path=path_str(), is_heading=True, line_start=i))
            order += 1
            continue
        if not ln.strip():
            flush()
            continue
        if buf_start is None:
            buf_start = i
        buf.append(ln)
    flush()
    return units


LOADERS = {".pdf": load_pdf, ".docx": load_docx, ".md": load_md, ".markdown": load_md, ".txt": load_md}


def load_corpus(folder: str | Path) -> list[Unit]:
    """Lee automáticamente todos los archivos soportados de la carpeta (orden alfabético)."""
    folder = Path(folder)
    files = sorted(f for f in folder.iterdir() if f.suffix.lower() in SUPPORTED)
    if not files:
        raise FileNotFoundError(f"No hay archivos soportados en {folder}")
    units: list[Unit] = []
    for f in files:
        units.extend(LOADERS[f.suffix.lower()](f))
    return units


def corpus_summary(units: list[Unit]) -> list[dict]:
    out: dict[str, dict] = {}
    for u in units:
        d = out.setdefault(u.doc, {"archivo": u.doc, "formato": u.fmt, "unidades": 0, "caracteres": 0})
        d["unidades"] += 1
        d["caracteres"] += len(u.text)
    return list(out.values())
