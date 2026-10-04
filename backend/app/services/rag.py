"""Lightweight RAG: chunk study text + TF-IDF retrieval with [S1] citations.

No external vector DB — runs on HF Spaces with stdlib only.
Chunks preserve source-file headers so citations are verifiable.
"""
import math
import re
from dataclasses import dataclass
from typing import Dict, List
from app.config import settings
from app.utils.logger import logger

_TOKEN_RE = re.compile(r"[a-zA-Z]{3,}")
_STOP = {
    "what", "how", "why", "when", "which", "with", "from", "into", "explain",
    "describe", "define", "discuss", "compare", "question", "marks", "answer",
    "study", "material", "notes", "using", "used", "this", "that", "have",
    "will", "their", "them", "then", "than",
}


@dataclass
class Chunk:
    id: str  # e.g. "S3"
    source: str  # e.g. "DBMS Module 1"
    text: str


def _tokens(text: str) -> List[str]:
    toks = [t.lower() for t in _TOKEN_RE.findall(text or "")]
    return [t for t in toks if t not in _STOP]


def chunk_study_text(study_text: str) -> List[Chunk]:
    """Split study text into overlapping chunks, tracking current source header."""
    max_chars = settings.RAG_CHUNK_CHARS
    overlap = settings.RAG_OVERLAP
    if not study_text or not study_text.strip():
        return []

    # Split while tracking "=== SOURCE FILE: X ===" headers (header may share a block with content)
    current_source = "Study materials"
    blocks: List[str] = []
    for para in study_text.split("\n\n"):
        text = para.strip()
        if not text:
            continue
        header = re.match(r"===\s*SOURCE FILE:\s*(.+?)\s*===", text)
        if header:
            current_source = header.group(1).strip()
            text = text[header.end():].strip()
            if not text:
                continue
        blocks.append((current_source, text))

    chunks: List[Chunk] = []
    buf_text = ""
    buf_source = blocks[0][0] if blocks else current_source
    idx = 0

    def flush():
        nonlocal buf_text, buf_source, idx
        if buf_text.strip():
            idx += 1
            chunks.append(Chunk(id=f"S{idx}", source=buf_source, text=buf_text.strip()))
            # overlap: keep tail for next chunk
            buf_text = buf_text[-overlap:] if len(buf_text) > overlap else ""

    for source, block in blocks:
        if source != buf_source and buf_text.strip():
            flush()
            buf_source = source
            buf_text = ""
        # split oversized blocks by sentence
        while len(buf_text) + len(block) + 2 > max_chars:
            room = max_chars - len(buf_text) - 2
            cut = block.rfind(". ", 0, max(room, 200))
            cut = cut + 1 if cut > 0 else room
            buf_text = (buf_text + "\n\n" + block[:cut]).strip()
            flush()
            buf_source = source
            block = block[cut:].strip()
            if not block:
                break
        if block:
            buf_text = (buf_text + "\n\n" + block).strip()
    flush()
    logger.info(f"[rag] chunked {len(study_text)} chars into {len(chunks)} chunks.")
    return chunks


def _tfidf_scores(query: str, chunks: List[Chunk]) -> List[float]:
    """Cosine TF-IDF between query and each chunk (pure stdlib)."""
    docs = [_tokens(c.text) for c in chunks]
    qtoks = _tokens(query)
    if not qtoks or not docs:
        return [0.0] * len(chunks)
    n = len(docs)
    df: Dict[str, int] = {}
    for toks in docs:
        for t in set(toks):
            df[t] = df.get(t, 0) + 1
    idf = {t: math.log((n + 1) / (d + 1)) + 1.0 for t, d in df.items()}

    def vec(toks: List[str]) -> Dict[str, float]:
        tf: Dict[str, float] = {}
        for t in toks:
            tf[t] = tf.get(t, 0) + 1.0
        total = len(toks) or 1
        return {t: (c / total) * idf.get(t, 1.0) for t, c in tf.items()}

    qv = vec(qtoks)
    qnorm = math.sqrt(sum(v * v for v in qv.values())) or 1.0
    scores = []
    for toks in docs:
        dv = vec(toks)
        dnorm = math.sqrt(sum(v * v for v in dv.values())) or 1.0
        dot = sum(qv.get(t, 0.0) * dv.get(t, 0.0) for t in set(qv) & set(dv))
        scores.append(dot / (qnorm * dnorm))
    # Small boost for definition/formula/diagram-dense chunks
    for i, c in enumerate(chunks):
        low = c.text.lower()
        if any(m in low for m in ("define", "definition", "refers to", "means")):
            scores[i] += 0.02
        if "{{IMAGE_ASSET:" in c.text:
            scores[i] += 0.03
    return scores


def retrieve_for_batch(study_text: str, batch_questions: List[dict], top_k: int | None = None) -> List[Chunk]:
    """Retrieve top-k chunks for a batch of questions. Never raises."""
    try:
        top_k = top_k or settings.RAG_TOP_K
        chunks = chunk_study_text(study_text)
        if not chunks:
            return []
        query = "\n".join(q.get("question_text", "") for q in batch_questions)
        scores = _tfidf_scores(query, chunks)
        ranked = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)
        # Keep chunks with signal; always keep at least top-1
        selected = [c for s, c in ranked[:top_k] if s > 0] or [ranked[0][1]]
        # Preserve original order for coherent context
        order = {c.id: i for i, c in enumerate(chunks)}
        selected.sort(key=lambda c: order[c.id])
        logger.info(f"[rag] retrieved {[c.id for c in selected]} for batch of {len(batch_questions)}.")
        return selected
    except Exception as e:
        logger.warning(f"[rag] retrieval failed, falling back: {e}")
        return []


def build_rag_context(chunks: List[Chunk], max_chars: int) -> str:
    """Format chunks as [S1]-tagged context within char budget."""
    parts = []
    total = 0
    for c in chunks:
        block = f"[{c.id} | {c.source}]\n{c.text}"
        if total + len(block) + 2 > max_chars and parts:
            break
        parts.append(block)
        total += len(block) + 2
    note = "\n\n[CITATION RULE: cite every factual claim inline as [S1], [S2], etc. Every answer MUST contain at least one citation.]\n"
    return "\n\n".join(parts) + note
