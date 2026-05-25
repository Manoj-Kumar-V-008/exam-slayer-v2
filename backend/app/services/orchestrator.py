import os
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Callable
from app.config import settings
from app.utils.logger import logger
from app.services.extractor import extract_document, run_ocr_fallback, get_ocr_candidate_text_length

MAX_CHAR_LIMIT = 120000

def enforce_payload_limits(study_text: str, qb_text: str) -> Tuple[str, str]:
    """
    Ensures the combined character count of study materials and question bank
    remains within safe processing limits (MAX_CHAR_LIMIT).
    If question bank is empty (STUDY_PACK), study materials get 100% of the budget.
    Otherwise, study materials get 75% and question bank gets 25% of the budget.
    """
    total_len = len(study_text) + len(qb_text)
    if total_len <= MAX_CHAR_LIMIT:
        return study_text, qb_text

    logger.warning(
        f"Combined text length ({total_len}) exceeds safety limit of {MAX_CHAR_LIMIT}. "
        "Applying intelligent truncation..."
    )

    if not qb_text:
        # STUDY_PACK mode (notes only) gets 100% of the limit
        truncated_study = study_text[:MAX_CHAR_LIMIT - 50] + "\n\n[...STUDY MATERIALS TRUNCATED FOR SIZE...]\n"
        return truncated_study, ""

    # ANSWER_PACK mode gets 75% / 25% split
    study_budget = int(MAX_CHAR_LIMIT * 0.75)
    qb_budget = int(MAX_CHAR_LIMIT * 0.25)

    # First, truncate study text to its budget if it exceeds it
    truncated_study = study_text
    if len(study_text) > study_budget:
        truncated_study = study_text[:study_budget] + "\n\n[...STUDY MATERIALS TRUNCATED FOR SIZE...]\n"

    # Truncate qb text to its budget if it exceeds it
    truncated_qb = qb_text
    if len(qb_text) > qb_budget:
        truncated_qb = qb_text[:qb_budget] + "\n\n[...QUESTION BANK TRUNCATED FOR SIZE...]\n"

    # If the combined length is still slightly over due to warning messages,
    # perform secondary adjustment by pulling from the end of study text.
    final_combined_len = len(truncated_study) + len(truncated_qb)
    if final_combined_len > MAX_CHAR_LIMIT:
        allowed_study_len = MAX_CHAR_LIMIT - len(truncated_qb) - 50
        if allowed_study_len > 0:
            truncated_study = study_text[:allowed_study_len] + "\n\n[...STUDY MATERIALS TRUNCATED FOR SIZE...]\n"
        else:
            truncated_study = "\n\n[...STUDY MATERIALS TRUNCATED FOR SIZE...]\n"

    return truncated_study, truncated_qb

def process_multi_source_job(
    job_id: str,
    study_file_paths: List[Path],
    study_file_names: List[str],
    question_bank_path: Optional[Path] = None,
    question_bank_name: Optional[str] = None,
    status_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    Orchestrates the sequential text and asset extraction for multiple study files
    and an optional question bank file.
    Applies OCR fallbacks, tags content namespaces, and enforces payload length limits.
    """
    logger.info(f"Orchestrated multi-source extraction started for job {job_id}")
    
    study_text_parts: List[str] = []
    all_assets: List[str] = []
    ocr_used_any = False
    
    # Report active stage: extracting study materials
    if status_callback:
        status_callback("extracting")
    
    # 1. Process all study files sequentially
    for path, name in zip(study_file_paths, study_file_names):
        logger.info(f"Processing study file: {name} ({path})")
        file_ext = name.split(".")[-1].lower() if "." in name else ""
        
        # Extract text & assets
        result = extract_document(str(path), file_ext, job_id)
        
        # Run OCR fallback if needed
        result = run_ocr_fallback(result, str(path), file_ext, job_id)
        
        if result.get("ocr_used", False):
            ocr_used_any = True
            
        all_assets.extend(result.get("assets", []))
        
        # Format text with source headers
        source_header = f"=== SOURCE FILE: {name} ===\n"
        study_text_parts.append(source_header + result.get("text", "").strip())
        
    study_materials_text = "\n\n".join(study_text_parts)
    
    # 2. Process question bank separately if provided
    question_bank_text = ""
    if question_bank_path and question_bank_name:
        # Report active stage: reading question bank
        if status_callback:
            status_callback("ocr_processing")
            
        logger.info(f"Processing question bank file: {question_bank_name} ({question_bank_path})")
        qb_ext = question_bank_name.split(".")[-1].lower() if "." in question_bank_name else ""
        
        result = extract_document(str(question_bank_path), qb_ext, job_id)
        result = run_ocr_fallback(result, str(question_bank_path), qb_ext, job_id)
        
        if result.get("ocr_used", False):
            ocr_used_any = True
            
        question_bank_text = f"=== QUESTION BANK SOURCE: {question_bank_name} ===\n" + result.get("text", "").strip()

    # 3. Apply AI Payload Protection Limits
    safe_study_text, safe_qb_text = enforce_payload_limits(study_materials_text, question_bank_text)
    
    # 4. Construct Final Combined Payload
    combined_payload_parts = []
    combined_payload_parts.append("=== STUDY MATERIALS ===")
    combined_payload_parts.append(safe_study_text)
    
    if safe_qb_text:
        combined_payload_parts.append("\n=== QUESTION BANK ===")
        combined_payload_parts.append(safe_qb_text)
        
    combined_raw_text = "\n".join(combined_payload_parts)
    
    logger.info(
        f"Multi-source extraction complete for job {job_id}. "
        f"Total study files processed: {len(study_file_paths)}. "
        f"Assets extracted: {len(all_assets)}. "
        f"Combined payload text size: {len(combined_raw_text)} chars."
    )
    
    return {
        "raw_text": combined_raw_text,
        "study_text": safe_study_text,
        "qb_text": safe_qb_text,
        "assets": all_assets,
        "ocr_used": ocr_used_any,
        "extracted_text_length": len(study_materials_text)
    }
