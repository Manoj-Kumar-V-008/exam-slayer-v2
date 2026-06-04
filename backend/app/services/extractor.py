import fitz  # PyMuPDF
import re
import shutil
import uuid
from docx import Document
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pathlib import Path
from typing import Dict, List, Any
from app.config import settings
from app.utils.logger import logger
import hashlib
from io import BytesIO
from PIL import Image

_IMAGE_ASSET_PATTERN = re.compile(r"\{\{IMAGE_ASSET:[^}]+\}\}")

def is_valid_academic_image(image_bytes: bytes, seen_hashes: set) -> bool:
    """
    Apply heuristics to filter out repeated logos, footers, Bullet icons,
    watermarks, and other decorative junk while keeping conceptual academic diagrams.
    """
    if not image_bytes:
        return False
    # Filter out tiny decorative icons / line slices (under 5KB)
    if len(image_bytes) < 5120:
        return False
        
    h = hashlib.md5(image_bytes).hexdigest()
    if seen_hashes is not None:
        if h in seen_hashes:
            return False
        seen_hashes.add(h)
        
    try:
        with Image.open(BytesIO(image_bytes)) as img:
            width, height = img.size
            # Filter out very thin horizontal/vertical dividers or bullet graphics
            if width < 60 or height < 60:
                return False
            if min(width, height) > 0:
                aspect_ratio = max(width, height) / min(width, height)
                # Filter out extreme aspect ratio layout lines/borders
                if aspect_ratio > 10.0:
                    return False
    except Exception:
        # Fallback: if Pillow cannot parse, but size is reasonable, keep it
        pass
        
    return True
_OCR_TEXT_SEPARATOR = "\n\n--- OCR RECOVERED TEXT ---\n\n"


def get_ocr_candidate_text_length(text: str) -> int:
    """Return extracted text length without generated image placeholders."""
    if not text:
        return 0
    return len(_IMAGE_ASSET_PATTERN.sub("", text).strip())


def _normalize_text(text: str) -> str:
    return " ".join((text or "").split()).strip()


def _asset_paths_from_result(result: Dict[str, Any]) -> List[Path]:
    return [settings.ASSETS_DIR / asset_name for asset_name in result.get("assets", [])]


def should_run_ocr_fallback(result: Dict[str, Any], file_ext: str) -> bool:
    """
    Decide whether OCR has real work to do for an extracted document.
    PDFs can be rendered directly; DOCX/PPTX need extracted image assets.
    """
    ext_clean = file_ext.lower().strip().replace(".", "")
    text_length = get_ocr_candidate_text_length(result.get("text", ""))

    if text_length >= settings.OCR_THRESHOLD:
        return False

    if ext_clean == "pdf":
        # Only run OCR fallback if the PDF has virtually zero text (scanned PDF).
        # Short digital PDFs (like a 14-question question bank) with readable text
        # should skip OCR fallback to prevent major latency/hang issues.
        return text_length < 40


    if ext_clean in ["docx", "doc", "pptx", "ppt"]:
        return any(path.exists() for path in _asset_paths_from_result(result))

    return False


def _merge_ocr_text(result: Dict[str, Any], ocr_text: str, job_id: str) -> Dict[str, Any]:
    """Append OCR text without duplicating text already recovered by direct extraction."""
    extracted_text = result.get("text", "")
    clean_extracted = _normalize_text(_IMAGE_ASSET_PATTERN.sub("", extracted_text))
    clean_ocr = _normalize_text(ocr_text)

    result["ocr_used"] = True

    if not clean_ocr:
        logger.info(f"OCR fallback for job {job_id} finished with empty text recovery.")
        return result

    if not _normalize_text(extracted_text):
        result["text"] = ocr_text.strip()
        logger.info(f"OCR recovered text length: {len(ocr_text)}. Replaced empty text.")
    elif clean_extracted and clean_ocr in clean_extracted:
        logger.info("OCR recovered text was already present in extracted text. Skipping merge.")
    else:
        result["text"] = extracted_text.rstrip() + _OCR_TEXT_SEPARATOR + ocr_text.strip()
        logger.info(f"OCR recovered text length: {len(ocr_text)}. Safely merged with extracted text.")

    return result


def extract_pdf_content(file_path: str, job_id: str, seen_hashes: set = None) -> Dict[str, Any]:
    """
    Extracts text page-by-page and retrieves embedded images from a PDF.
    Inserts inline placeholders like {{IMAGE_ASSET:filename}} in layout order.
    """
    logger.info(f"Starting PDF extraction for job_id={job_id}, file_path={file_path}")
    
    extracted_text_parts: List[str] = []
    extracted_assets: List[str] = []
    image_counter = 1
    
    try:
        doc = fitz.open(file_path)
    except Exception as e:
        logger.error(f"Failed to open PDF document {file_path}: {str(e)}")
        raise e
        
    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_elements = []
            
            # 1. Retrieve all text blocks
            blocks = page.get_text("blocks")
            for b in blocks:
                x0, y0, x1, y1, text_val, _, block_type = b
                if block_type == 0:  # Text block
                    page_elements.append({
                        "type": "text",
                        "bbox": (x0, y0, x1, y1),
                        "content": text_val
                    })
            
            # 2. Retrieve all images and their spatial coordinates
            page_height = page.rect.height
            image_list = page.get_images(full=True)
            for img in image_list:
                xref = img[0]
                rects = page.get_image_rects(xref)
                for rect in rects:
                    if page_height > 0:
                        is_header = rect.y1 <= page_height * 0.09
                        is_footer = rect.y0 >= page_height * 0.91
                        if is_header or is_footer:
                            logger.info(
                                f"Skipping header/footer image xref={xref} at y=({rect.y0:.1f}, {rect.y1:.1f}) "
                                f"on page {page_num} (page height={page_height:.1f})"
                            )
                            continue
                            
                    page_elements.append({
                        "type": "image",
                        "bbox": (rect.x0, rect.y0, rect.x1, rect.y1),
                        "xref": xref
                    })
            
            # 3. Sort elements on the page vertically (top-to-bottom) then horizontally (left-to-right)
            page_elements.sort(key=lambda e: (round(e["bbox"][1] / 5.0) * 5.0, e["bbox"][0]))
            
            page_text_parts: List[str] = []
            for element in page_elements:
                if element["type"] == "text":
                    page_text_parts.append(element["content"])
                elif element["type"] == "image":
                    xref = element["xref"]
                    try:
                        base_image = doc.extract_image(xref)
                        if base_image:
                            image_bytes = base_image["image"]
                            if not is_valid_academic_image(image_bytes, seen_hashes):
                                logger.info(f"Skipped image xref={xref} on page {page_num} for job {job_id} due to academic heuristics.")
                                continue
                                
                            image_ext = base_image["ext"] or "png"
                            
                            if image_ext == "jpeg":
                                image_ext = "jpg"
                                
                            filename = f"{job_id}_img_{image_counter}.{image_ext}"
                            out_path = settings.ASSETS_DIR / filename
                            
                            with open(out_path, "wb") as img_file:
                                img_file.write(image_bytes)
                                
                            extracted_assets.append(filename)
                            page_text_parts.append(f"\n{{{{IMAGE_ASSET:{filename}}}}}\n")
                            image_counter += 1
                    except Exception as img_err:
                        logger.error(
                            f"Failed to extract image xref={xref} on page {page_num} for job {job_id}: {str(img_err)}"
                        )
            
            if page_text_parts:
                page_content = "".join(page_text_parts)
                extracted_text_parts.append(page_content)
                
        full_text = "\n\n".join(extracted_text_parts)
        logger.info(f"Successfully processed PDF job_id={job_id}. Extracted {len(extracted_assets)} images.")
        return {
            "text": full_text,
            "assets": extracted_assets
        }
        
    finally:
        doc.close()

def extract_docx_content(file_path: str, job_id: str, seen_hashes: set = None) -> Dict[str, Any]:
    """
    Extracts text paragraphs and embedded inline images from a Word (.docx) file.
    Inserts inline placeholders like {{IMAGE_ASSET:filename}} in document order.
    """
    logger.info(f"Starting DOCX extraction for job_id={job_id}, file_path={file_path}")
    
    extracted_text_parts: List[str] = []
    extracted_assets: List[str] = []
    image_counter = 1
    
    try:
        doc = Document(file_path)
    except Exception as e:
        logger.error(f"Failed to open DOCX document {file_path}: {str(e)}")
        raise e
        
    # XML namespace mapping for extracting embedded relationships in runs
    embed_ns = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
    
    for paragraph in doc.paragraphs:
        para_text = ""
        for run in paragraph.runs:
            # Check if this run contains an embedded drawing element/blip
            blips = run.element.xpath('.//a:blip')
            if blips:
                for blip in blips:
                    rId = blip.get(embed_ns)
                    if rId and rId in doc.part.related_parts:
                        try:
                            image_part = doc.part.related_parts[rId]
                            image_bytes = image_part.image.blob
                            if not is_valid_academic_image(image_bytes, seen_hashes):
                                logger.info(f"Skipped DOCX image rId={rId} for job {job_id} due to academic heuristics.")
                                continue
                                
                            content_type = image_part.content_type
                            
                            # Determine extension based on content type
                            image_ext = content_type.split("/")[-1] if "/" in content_type else "png"
                            if image_ext == "jpeg":
                                image_ext = "jpg"
                                
                            filename = f"{job_id}_docx_img_{image_counter}.{image_ext}"
                            out_path = settings.ASSETS_DIR / filename
                            
                            with open(out_path, "wb") as img_file:
                                img_file.write(image_bytes)
                                
                            extracted_assets.append(filename)
                            para_text += f"\n{{{{IMAGE_ASSET:{filename}}}}}\n"
                            image_counter += 1
                        except Exception as img_err:
                            logger.error(f"Failed to extract DOCX image relationship rId={rId}: {str(img_err)}")
            else:
                para_text += run.text
                
        if para_text.strip():
            extracted_text_parts.append(para_text)

    # Extract text from tables to handle question banks or materials structured in grids
    for table in doc.tables:
        for row in table.rows:
            row_text = []
            seen_cells = set()
            for cell in row.cells:
                if cell not in seen_cells:
                    seen_cells.add(cell)
                    cell_text = cell.text.strip()
                    if cell_text:
                        row_text.append(cell_text)
            if row_text:
                extracted_text_parts.append(" | ".join(row_text))
            
    full_text = "\n\n".join(extracted_text_parts)
    logger.info(f"Successfully processed DOCX job_id={job_id}. Extracted {len(extracted_assets)} images.")
    return {
        "text": full_text,
        "assets": extracted_assets
    }

def extract_pptx_content(file_path: str, job_id: str, seen_hashes: set = None) -> Dict[str, Any]:
    """
    Extracts text and embedded images from a PowerPoint (.pptx) file slide by slide,
    sorting slide shapes top-to-bottom and preserving slide separation.
    """
    logger.info(f"Starting PPTX extraction for job_id={job_id}, file_path={file_path}")
    
    extracted_text_parts: List[str] = []
    extracted_assets: List[str] = []
    image_counter = 1
    
    try:
        prs = Presentation(file_path)
    except Exception as e:
        logger.error(f"Failed to open PPTX presentation {file_path}: {str(e)}")
        raise e
        
    for slide_idx, slide in enumerate(prs.slides):
        slide_text_elements = []
        slide_text_elements.append(f"--- SLIDE {slide_idx + 1} ---")
        
        # Sort shapes top-to-bottom, left-to-right to ensure reading flow
        shapes = sorted(
            slide.shapes, 
            key=lambda s: (s.top, s.left) if hasattr(s, 'top') and s.top is not None else (0, 0)
        )
        
        for shape in shapes:
            if shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    para_text = paragraph.text.strip()
                    if para_text:
                        slide_text_elements.append(para_text)
            elif shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                try:
                    image = shape.image
                    image_bytes = image.blob
                    if not is_valid_academic_image(image_bytes, seen_hashes):
                        logger.info(f"Skipped PPTX image for job {job_id} due to academic heuristics.")
                        continue
                        
                    image_ext = image.ext or "png"
                    if image_ext == "jpeg":
                        image_ext = "jpg"
                        
                    filename = f"{job_id}_pptx_img_{image_counter}.{image_ext}"
                    out_path = settings.ASSETS_DIR / filename
                    
                    with open(out_path, "wb") as img_file:
                        img_file.write(image_bytes)
                        
                    extracted_assets.append(filename)
                    slide_text_elements.append(f"\n{{{{IMAGE_ASSET:{filename}}}}}\n")
                    image_counter += 1
                except Exception as img_err:
                    logger.error(f"Failed to extract PPTX slide image: {str(img_err)}")
                    
        slide_content = "\n".join(slide_text_elements)
        extracted_text_parts.append(slide_content)
        
    full_text = "\n\n".join(extracted_text_parts)
    logger.info(f"Successfully processed PPTX job_id={job_id}. Extracted {len(extracted_assets)} images.")
    return {
        "text": full_text,
        "assets": extracted_assets
    }

def extract_document(file_path: str, extension: str, job_id: str, seen_hashes: set = None) -> Dict[str, Any]:
    """
    Dispatcher routing the document to the corresponding extractor service based on extension.
    """
    ext_clean = extension.lower().strip().replace(".", "")
    
    if ext_clean == "pdf":
        result = extract_pdf_content(file_path, job_id, seen_hashes)
    elif ext_clean in ["docx", "doc"]:
        result = extract_docx_content(file_path, job_id, seen_hashes)
    elif ext_clean in ["pptx", "ppt"]:
        result = extract_pptx_content(file_path, job_id, seen_hashes)
    else:
        logger.error(f"Unsupported document extension: {extension}")
        raise ValueError(f"Unsupported document extension: .{ext_clean}")
        
    result["ocr_used"] = False
    return result

def run_ocr_fallback(result: Dict[str, Any], file_path: str, file_ext: str, job_id: str) -> Dict[str, Any]:
    """
    Triggers OCR fallback processing for PDF, DOCX, or PPTX when direct extraction
    produced too little text. Returns the updated result dict with ocr_used set
    to True only when the OCR pipeline actually ran.
    """
    ext_clean = file_ext.lower().strip().replace(".", "")
    result["ocr_used"] = False

    if not should_run_ocr_fallback(result, file_ext):
        logger.info(
            f"Skipping OCR fallback for job {job_id}. "
            f"Text length={get_ocr_candidate_text_length(result.get('text', ''))}, "
            f"threshold={settings.OCR_THRESHOLD}, assets={len(result.get('assets', []))}."
        )
        return result

    ocr_text = ""
    ocr_triggered = False
    
    if ext_clean == "pdf":
        logger.info(f"Running PDF OCR fallback for job {job_id} on {file_path}...")
        doc = None
        try:
            from app.services.ocr import OCRService

            settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            doc = fitz.open(file_path)
            num_pages = len(doc)
            pages_to_ocr = min(num_pages, settings.OCR_MAX_PAGES)
            if num_pages > settings.OCR_MAX_PAGES:
                logger.warning(
                    f"PDF has {num_pages} pages, which exceeds the limit of {settings.OCR_MAX_PAGES}. "
                    f"OCR fallback will only process the first {settings.OCR_MAX_PAGES} pages."
                )
                
            temp_dir_path = settings.UPLOAD_DIR / f"{job_id}_ocr_{uuid.uuid4().hex}"
            temp_img_paths: List[Path] = []
            try:
                temp_dir_path.mkdir(parents=True, exist_ok=False)
                for page_num in range(pages_to_ocr):
                    page = doc[page_num]
                    pix = page.get_pixmap(dpi=150)
                    temp_img_path = temp_dir_path / f"page_{page_num + 1}.png"
                    pix.save(str(temp_img_path))
                    temp_img_paths.append(temp_img_path)

                if not temp_img_paths:
                    logger.info(f"No PDF pages available for OCR fallback on job {job_id}.")
                    return result

                logger.info(
                    f"Generated {len(temp_img_paths)} temporary images in {temp_dir_path}. "
                    "Running OCRService..."
                )
                ocr_text = OCRService.extract_text_from_images(temp_img_paths)
                logger.info(f"Temporary image folder {temp_dir_path} cleaned up automatically.")
            finally:
                shutil.rmtree(temp_dir_path, ignore_errors=True)

            ocr_triggered = True
        except Exception as e:
            logger.error(f"Failed to perform PDF OCR fallback for job {job_id}: {str(e)}")
        finally:
            if doc is not None:
                doc.close()

    elif ext_clean in ["docx", "doc", "pptx", "ppt"]:
        image_paths = [path for path in _asset_paths_from_result(result) if path.exists()]
        if image_paths:
            logger.info(
                f"Running {ext_clean.upper()} OCR fallback for job {job_id} "
                f"using {len(image_paths)} extracted assets..."
            )
            try:
                from app.services.ocr import OCRService
                ocr_text = OCRService.extract_text_from_images(image_paths)
                ocr_triggered = True
            except Exception as e:
                logger.error(f"Failed to perform {ext_clean.upper()} OCR fallback for job {job_id}: {str(e)}")
        else:
            logger.info(f"Skipping {ext_clean.upper()} OCR fallback (no extracted asset files found to run OCR on).")

    if ocr_triggered:
        return _merge_ocr_text(result, ocr_text, job_id)

    return result
