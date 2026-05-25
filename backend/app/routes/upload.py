import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from app.config import settings
from app.models.schemas import UploadResponse, JobStatus, ProductMode
from app.utils.jobs_store import jobs_db
from app.utils.logger import logger

router = APIRouter(prefix="/upload", tags=["Upload"])

def run_pdf_extraction_pipeline(
    job_id: str,
    study_file_paths: List[str],
    study_file_names: List[str],
    question_bank_path: Optional[str],
    question_bank_name: Optional[str],
    mode: ProductMode
):
    """Background task to run multi-source extraction, AI cleanup, and WeasyPrint PDF generation based on mode."""
    logger.info(f"Background extraction pipeline started for job {job_id} in {mode} mode")
    
    # 1. Start with extracting status
    jobs_db[job_id]["status"] = JobStatus.EXTRACTING
    
    try:
        from app.services.orchestrator import process_multi_source_job
        from app.services.ai import generate_solved_answers, clean_study_notes
        from app.services.template import render_answer_pack_html, render_study_pack_html
        from app.services.pdf_generator import generate_pdf
        from pathlib import Path
        
        study_paths = [Path(p) for p in study_file_paths]
        qb_path = Path(question_bank_path) if question_bank_path else None
        
        # Define inline callback to report status changes during extraction stages
        def update_job_status(new_status_str: str):
            try:
                enum_status = JobStatus(new_status_str)
                jobs_db[job_id]["status"] = enum_status
                logger.info(f"Background pipeline status updated for job {job_id}: {enum_status}")
            except Exception as e:
                logger.error(f"Failed to map status '{new_status_str}': {str(e)}")
        
        # 2. Perform multi-source orchestration with status callbacks
        extraction_result = process_multi_source_job(
            job_id=job_id,
            study_file_paths=study_paths,
            study_file_names=study_file_names,
            question_bank_path=qb_path,
            question_bank_name=question_bank_name,
            status_callback=update_job_status
        )
        
        # 3. OCR update
        ocr_used = extraction_result["ocr_used"]
        if ocr_used:
            jobs_db[job_id]["ocr_used"] = True
            
        # 4. Update status to AI_PROCESSING (solving or compiling)
        jobs_db[job_id]["status"] = JobStatus.AI_PROCESSING
        
        if mode == ProductMode.STUDY_PACK:
            logger.info(f"Extraction complete for job {job_id}. Starting Gemini AI study guide generation...")
            
            # Call Gemini study guide compiler
            study_pack_data = clean_study_notes(extraction_result["study_text"])
            
            # Correct asset filenames
            from app.utils.asset_sanitizer import sanitize_embedded_assets
            sanitize_embedded_assets(study_pack_data, job_id, extraction_result["assets"])
            
            # 6. Update status to PDF_GENERATING (compiling PDF)
            jobs_db[job_id]["status"] = JobStatus.PDF_GENERATING
            logger.info(f"Gemini compiled study guide successfully for job {job_id}. Rendering template HTML...")
            
            # 7. Render HTML content using Jinja2
            html_content = render_study_pack_html(study_pack_data)
            
            # 8. Generate PDF via WeasyPrint
            pdf_filename = f"{job_id}_study_pack.pdf"
            pdf_output_path = settings.OUTPUTS_DIR / pdf_filename
            generate_pdf(html_content, pdf_output_path)
            
            # 9. Update job db on complete success
            jobs_db[job_id].update({
                "status": JobStatus.COMPLETED,
                "completed_at": datetime.utcnow().isoformat(),
                "extracted_text_length": extraction_result["extracted_text_length"],
                "extracted_asset_count": len(extraction_result["assets"]),
                "assets": extraction_result["assets"],
                "ocr_used": ocr_used,
                "study_pack": study_pack_data,
                "pdf_file": pdf_filename,
                "pdf_url": f"/api/v1/jobs/download/{job_id}"
            })
        else:  # ANSWER_PACK mode
            logger.info(f"Extraction complete for job {job_id}. Starting Gemini AI question parsing...")
            
            # Parse questions from question bank text
            from app.services.question_parser import parse_questions_from_bank
            parsed_questions = parse_questions_from_bank(extraction_result["qb_text"])
            logger.info(f"Parsed {len(parsed_questions)} questions from bank. Starting Gemini AI solving...")
            
            # Call Gemini solver passing the study materials text and the parsed questions list
            answer_pack_data = generate_solved_answers(
                study_text=extraction_result["study_text"],
                parsed_questions=parsed_questions
            )
            
            # Correct any UUID transcription errors in asset filenames
            from app.utils.asset_sanitizer import sanitize_embedded_assets
            sanitize_embedded_assets(answer_pack_data, job_id, extraction_result["assets"])
            
            # 6. Update status to PDF_GENERATING (compiling PDF)
            jobs_db[job_id]["status"] = JobStatus.PDF_GENERATING
            logger.info(f"Gemini solved answers successfully for job {job_id}. Rendering template HTML...")
            
            # 7. Render HTML content using Jinja2
            html_content = render_answer_pack_html(answer_pack_data)
            
            # 8. Generate PDF via WeasyPrint
            pdf_filename = f"{job_id}_answer_pack.pdf"
            pdf_output_path = settings.OUTPUTS_DIR / pdf_filename
            generate_pdf(html_content, pdf_output_path)
            
            # 9. Update job db on complete success
            jobs_db[job_id].update({
                "status": JobStatus.COMPLETED,
                "completed_at": datetime.utcnow().isoformat(),
                "extracted_text_length": extraction_result["extracted_text_length"],
                "extracted_asset_count": len(extraction_result["assets"]),
                "assets": extraction_result["assets"],
                "ocr_used": ocr_used,
                "answer_pack": answer_pack_data,
                "pdf_file": pdf_filename,
                "pdf_url": f"/api/v1/jobs/download/{job_id}"
            })
            
        logger.info(f"Background job {job_id} completed successfully.")
        
    except Exception as e:
        logger.error(f"Background job {job_id} failed: {str(e)}")
        jobs_db[job_id].update({
            "status": JobStatus.FAILED,
            "completed_at": datetime.utcnow().isoformat(),
            "error_message": str(e)
        })

@router.post("", response_model=UploadResponse)
async def upload_file(
    background_tasks: BackgroundTasks, 
    mode: ProductMode = Form(..., description="The generation mode: STUDY_PACK or ANSWER_PACK"),
    study_files: List[UploadFile] = File(...),
    question_bank: Optional[UploadFile] = File(None)
):
    # 1. Validation checks
    if not (1 <= len(study_files) <= 5):
        logger.warning(f"Rejected upload: study_files count is {len(study_files)} (must be 1-5)")
        raise HTTPException(
            status_code=400,
            detail=f"Study files count must be between 1 and 5. Received: {len(study_files)}"
        )
        
    supported_formats = {"pdf", "docx", "pptx"}
    
    study_file_names = []
    for sf in study_files:
        ext = sf.filename.split(".")[-1].lower() if "." in sf.filename else ""
        if ext not in supported_formats:
            logger.warning(f"Rejected file format: {sf.filename}")
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format '{ext}'. Supported formats: PDF, DOCX, PPTX."
            )
        study_file_names.append(sf.filename)
        
    # Question bank file is REQUIRED for ANSWER_PACK mode
    question_bank_name = None
    if mode == ProductMode.ANSWER_PACK:
        if not question_bank or not question_bank.filename:
            logger.warning("Rejected upload: missing required question_bank file for ANSWER_PACK mode.")
            raise HTTPException(
                status_code=400,
                detail="Question bank file is required for ANSWER_PACK mode."
            )
            
        ext = question_bank.filename.split(".")[-1].lower() if "." in question_bank.filename else ""
        if ext not in supported_formats:
            logger.warning(f"Rejected question bank format: {question_bank.filename}")
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported question bank format '{ext}'. Supported formats: PDF, DOCX, PPTX."
            )
        question_bank_name = question_bank.filename
    else:
        # In STUDY_PACK mode, ignore question_bank if uploaded or do not enforce it
        if question_bank and question_bank.filename:
            ext = question_bank.filename.split(".")[-1].lower() if "." in question_bank.filename else ""
            if ext in supported_formats:
                question_bank_name = question_bank.filename
            else:
                question_bank = None  # discard invalid optional file

    # 2. File size protection (MVP limit: 40MB total)
    MAX_TOTAL_SIZE = 40 * 1024 * 1024  # 40MB
    total_size = 0
    
    for sf in study_files:
        sf.file.seek(0, 2)
        total_size += sf.file.tell()
        sf.file.seek(0)
        
    if question_bank and question_bank.filename:
        question_bank.file.seek(0, 2)
        total_size += question_bank.file.tell()
        question_bank.file.seek(0)
        
    if total_size > MAX_TOTAL_SIZE:
        logger.warning(f"Rejected upload: combined size of {total_size / 1024 / 1024:.2f}MB exceeds 40MB threshold")
        raise HTTPException(
            status_code=400,
            detail=f"Total combined upload size exceeds 40MB limit. Current: {total_size / 1024 / 1024:.2f}MB."
        )

    # 3. Create job directory & save files
    job_id = str(uuid.uuid4())
    job_dir = settings.UPLOAD_DIR / job_id
    try:
        job_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create job directory: {str(e)}")
        raise HTTPException(status_code=500, detail="Could not create directory for upload files.")
        
    study_file_paths = []
    for sf in study_files:
        safe_name = f"study_{uuid.uuid4().hex}_{sf.filename}"
        path = job_dir / safe_name
        try:
            content = await sf.read()
            with open(path, "wb") as f:
                f.write(content)
            study_file_paths.append(str(path))
        except Exception as e:
            logger.error(f"Failed to write study file {sf.filename}: {str(e)}")
            raise HTTPException(status_code=500, detail="Could not save study materials.")
            
    question_bank_path = None
    if question_bank and question_bank.filename:
        safe_qb_name = f"qb_{uuid.uuid4().hex}_{question_bank.filename}"
        qb_path = job_dir / safe_qb_name
        try:
            content = await question_bank.read()
            with open(qb_path, "wb") as f:
                f.write(content)
            question_bank_path = str(qb_path)
        except Exception as e:
            logger.error(f"Failed to write question bank {question_bank.filename}: {str(e)}")
            raise HTTPException(status_code=500, detail="Could not save question bank.")

    # 4. Map job database entry with proper structured fields
    primary_name = study_file_names[0] if study_file_names else "Study materials"
    
    jobs_db[job_id] = {
        "job_id": job_id,
        "mode": mode,
        "status": JobStatus.UPLOADED,
        "file_name": primary_name,  # primary representative name
        "study_file_names": study_file_names,
        "question_bank_name": question_bank_name,
        "study_file_count": len(study_file_names),
        "created_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "error_message": None,
        "study_pack": None,
        "answer_pack": None,
        "pdf_url": None,
        "extracted_text_length": 0,
        "extracted_asset_count": 0,
        "assets": [],
        "pdf_file": None,
        "ocr_used": False
    }

    # 5. Queue background task
    background_tasks.add_task(
        run_pdf_extraction_pipeline,
        job_id,
        study_file_paths,
        study_file_names,
        question_bank_path,
        question_bank_name,
        mode
    )

    return UploadResponse(
        job_id=job_id,
        message=f"Multi-source files uploaded successfully. {mode} pipeline started.",
        status=JobStatus.UPLOADED,
        mode=mode
    )
