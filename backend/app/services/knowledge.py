"""Approved educational resources: upload validation, chunking and lexical retrieval.

Retrieval is TF-IDF over paragraph chunks. It is portable (SQLite and PostgreSQL), explainable and
needs no embedding service. Professor-only resources are never returned for student-facing use.
"""

from __future__ import annotations

import math
import re
import uuid
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.knowledge import EducationalResource, ResourceChunk

ALLOWED_EXTENSIONS = (".txt", ".md")
CHUNK_CHARS = 900
_WORD = re.compile(r"[\w؀-ۿ]+", re.UNICODE)
_STOP = set(
    "the a an and or of to in on for with is are was were be by at as it this that from your you "
    "their they he she we our not but if then than so can will would should into about".split()
)


class ResourceError(ValueError):
    pass


def _tokens(text: str) -> list[str]:
    return [
        w
        for w in (m.group(0).lower() for m in _WORD.finditer(text))
        if w not in _STOP and len(w) > 2
    ]


def extract_text(filename: str, raw: bytes, max_bytes: int) -> str:
    if not filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise ResourceError("Only .txt and .md files are accepted.")
    if len(raw) > max_bytes:
        raise ResourceError(f"File too large (limit {max_bytes // 1000} KB).")
    if b"\x00" in raw:
        raise ResourceError("Binary files are not accepted.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ResourceError("The file must be UTF-8 text.") from None
    text = text.replace("\r\n", "\n").strip()
    if len(text) < 20:
        raise ResourceError("The file is empty or too short.")
    return text


def chunk(text: str) -> list[tuple[str, str]]:
    """Split into (heading, text) chunks along Markdown headings and paragraphs."""
    chunks: list[tuple[str, str]] = []
    heading = ""
    buf: list[str] = []

    def flush() -> None:
        body = "\n\n".join(buf).strip()
        if body:
            chunks.append((heading, body))
        buf.clear()

    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block:
            continue
        m = re.match(r"^#{1,6}\s+(.*)", block)
        if m:
            flush()
            heading = m.group(1).strip()[:300]
            rest = block[m.end() :].strip()
            if rest:
                buf.append(rest)
            continue
        if sum(len(b) for b in buf) + len(block) > CHUNK_CHARS:
            flush()
        buf.append(block)
    flush()
    return chunks


def create_resource(
    db: Session,
    *,
    title: str,
    filename: str,
    text: str,
    specialization_id: uuid.UUID | None,
    visibility: str,
    uploaded_by: uuid.UUID,
) -> EducationalResource:
    if visibility not in ("students", "professors"):
        raise ResourceError("visibility must be 'students' or 'professors'")
    previous = db.scalar(
        select(EducationalResource)
        .where(EducationalResource.title == title)
        .order_by(EducationalResource.version.desc())
    )
    resource = EducationalResource(
        title=title.strip()[:300],
        source_filename=filename[:255],
        specialization_id=specialization_id,
        visibility=visibility,
        uploaded_by_id=uploaded_by,
        version=(previous.version + 1) if previous else 1,
    )
    resource.chunks = [
        ResourceChunk(position=i, heading=h, text=t) for i, (h, t) in enumerate(chunk(text))
    ]
    db.add(resource)
    db.flush()
    return resource


def search(
    db: Session,
    query: str,
    *,
    specialization_id: uuid.UUID | None = None,
    include_professor_only: bool = False,
    limit: int = 3,
) -> list[dict]:
    q_tokens = _tokens(query)
    if not q_tokens:
        return []
    stmt = select(ResourceChunk, EducationalResource).join(
        EducationalResource, ResourceChunk.resource_id == EducationalResource.id
    )
    if not include_professor_only:
        stmt = stmt.where(EducationalResource.visibility == "students")
    if specialization_id is not None:
        stmt = stmt.where(
            (EducationalResource.specialization_id == specialization_id)
            | (EducationalResource.specialization_id.is_(None))
        )
    rows = list(db.execute(stmt).all())
    if not rows:
        return []
    docs = [Counter(_tokens(c.heading + " " + c.text)) for c, _ in rows]
    n = len(docs)
    df = Counter(t for d in docs for t in set(d))
    scored = []
    for (chunk_row, res), counts in zip(rows, docs, strict=True):
        total = sum(counts.values()) or 1
        score = sum(
            (counts[t] / total) * math.log(1 + n / (1 + df[t]))
            for t in set(q_tokens)
            if t in counts
        )
        if score > 0:
            scored.append((score, chunk_row, res))
    scored.sort(key=lambda s: s[0], reverse=True)
    return [
        {
            "resource_id": str(res.id),
            "title": res.title,
            "version": res.version,
            "heading": c.heading,
            "text": c.text,
            "score": round(s, 4),
        }
        for s, c, res in scored[:limit]
    ]
