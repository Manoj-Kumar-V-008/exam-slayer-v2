"""Vision-grounded page renders for Gemini multimodal generation.

Renders PDF pages to downscaled JPEGs so the model sees diagrams, tables,
and formulas — not just extracted text + {{IMAGE_ASSET:...}} filenames.
Diagram-heavy pages are prioritized within a per-job page budget.
"""
from pathlib import Path
from typing import List, Tuple
from app.config import settings
from app.utils.logger import logger


def _score_pdf_pages(doc) -> List[Tuple[int, int]]:
    """Score pages by embedded-image count (diagram proxy). Returns [(page_num, score)]."""
    scored = []
    for page_num in range(len(doc)):
        try:
            image_count = len(doc[page_num].get_images(full=True))
        except Exception:
            image_count = 0
        scored.append((page_num, image_count))
    return scored


def render_pdf_page_images(
    pdf_path: str | Path,
    job_id: str,
    output_dir: Path | None = None,
    max_pages: int | None = None,
    dpi: int | None = None,
) -> List[Path]:
    """Render top-priority PDF pages to JPEG. Never raises — returns [] on failure."""
    from io import BytesIO

    import fitz
    from PIL import Image

    max_pages = max_pages or settings.VISION_MAX_PAGES
    dpi = dpi or settings.VISION_DPI
    output_dir = Path(output_dir) if output_dir else (settings.UPLOAD_DIR / str(job_id) / "vision")

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.warning(f"[vision] cannot create dir {output_dir}: {e}")
        return []

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        logger.warning(f"[vision] cannot open PDF {pdf_path}: {e}")
        return []

    try:
        num_pages = len(doc)
        if num_pages == 0:
            return []
        # Prioritize diagram-heavy pages, keep reading order for the selected set.
        scored = _score_pdf_pages(doc)
        scored.sort(key=lambda x: x[1], reverse=True)
        selected = sorted(p for p, _ in scored[:max_pages])
        logger.info(f"[vision] {pdf_path}: {num_pages} pages, rendering {len(selected)}: {selected}")

        rendered: List[Path] = []
        for page_num in selected:
            try:
                page = doc[page_num]
                pix = page.get_pixmap(dpi=dpi)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                img.thumbnail((settings.VISION_MAX_DIM, settings.VISION_MAX_DIM), Image.LANCZOS)
                out_path = output_dir / f"{job_id}_vision_p{page_num + 1}.jpg"
                img.save(str(out_path), "JPEG", quality=settings.VISION_JPEG_QUALITY, optimize=True)
                rendered.append(out_path)
            except Exception as e:
                logger.warning(f"[vision] page {page_num} render failed: {e}")
                continue
        logger.info(f"[vision] rendered {len(rendered)} page images to {output_dir}")
        return rendered
    finally:
        try:
            doc.close()
        except Exception:
            pass
