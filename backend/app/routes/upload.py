import uuid
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from app.config import settings
from app.models.schemas import UploadResponse, JobStatus
from app.utils.jobs_store import jobs_db
from app.utils.logger import logger

router = APIRouter(prefix="/upload", tags=["Upload"])

def run_pdf_extraction_pipeline(job_id: str, file_path: str, file_name: str):
    """Background task to run PDF/DOCX/PPTX extraction, Gemini AI cleanup, and WeasyPrint PDF generation."""
    logger.info(f"Background extraction pipeline started for job {job_id} ({file_name})")
    
    # 1. Update status to EXTRACTING
    jobs_db[job_id]["status"] = JobStatus.EXTRACTING
    
    try:
        from app.services.extractor import (
            extract_document,
            get_ocr_candidate_text_length,
            run_ocr_fallback,
            should_run_ocr_fallback,
        )
        from app.services.ai import clean_study_notes
        from app.services.template import render_study_pack_html
        from app.services.pdf_generator import generate_pdf
        
        # Determine extension
        file_ext = file_name.split(".")[-1].lower() if "." in file_name else ""
        
        # 2. Perform document extraction (text and image assets)
        result = extract_document(str(file_path), file_ext, job_id)
        
        # 3. Trigger OCR only when low extracted text has OCR-able inputs
        extracted_text_length = get_ocr_candidate_text_length(result.get("text", ""))
        if should_run_ocr_fallback(result, file_ext):
            logger.info(
                f"Extracted text length ({extracted_text_length}) is below OCR threshold "
                f"({settings.OCR_THRESHOLD}). Triggering OCR fallback for job {job_id}..."
            )
            jobs_db[job_id]["status"] = JobStatus.OCR_PROCESSING
            result = run_ocr_fallback(result, str(file_path), file_ext, job_id)
            
            if result.get("ocr_used"):
                logger.info(
                    f"OCR fallback complete for job {job_id}. "
                    f"Final text length: {len(result.get('text', ''))}."
                )
            else:
                logger.info(f"OCR fallback was attempted for job {job_id} but did not produce usable output.")
        else:
            if extracted_text_length < settings.OCR_THRESHOLD:
                logger.info(
                    f"Extracted text length ({extracted_text_length}) is below OCR threshold "
                    f"({settings.OCR_THRESHOLD}), but no OCR-able inputs were found for job {job_id}."
                )
            else:
                logger.info(
                    f"Extracted text length ({extracted_text_length}) meets threshold. "
                    f"Skipping OCR fallback for job {job_id}."
                )
        
        # 4. Update status to AI_PROCESSING before calling Gemini
        jobs_db[job_id]["status"] = JobStatus.AI_PROCESSING
        logger.info(f"Extraction complete for job {job_id}. Starting Gemini AI cleanup...")
        
        # 5. Perform Gemini cleanup
        study_pack_data = clean_study_notes(result["text"])
        
        # Correct any UUID transcription errors in asset filenames
        from app.utils.asset_sanitizer import sanitize_embedded_assets
        sanitize_embedded_assets(study_pack_data, job_id, result["assets"])
        
        # 6. Update status to PDF_GENERATING before rendering and compiling PDF
        jobs_db[job_id]["status"] = JobStatus.PDF_GENERATING
        logger.info(f"Gemini cleanup succeeded for job {job_id}. Rendering HTML template...")
        
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
            "extracted_text_length": len(result["text"]),
            "extracted_asset_count": len(result["assets"]),
            "assets": result["assets"],
            "ocr_used": result.get("ocr_used", False),
            "study_pack": study_pack_data,
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
    file: UploadFile = File(...)
):
    # Validate file extension
    file_ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    supported_docs = {"pdf", "docx", "doc", "pptx", "ppt"}
    if file_ext not in settings.ALLOWED_EXTENSIONS or file_ext not in supported_docs:
        logger.warning(f"Rejected file with unsupported extension: {file.filename}")
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Supported formats: PDF, DOCX, PPTX. Received: '.{file_ext}'"
        )
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # Secure filename and save path
    safe_filename = f"{job_id}_{file.filename}"
    file_path = settings.UPLOAD_DIR / safe_filename
    
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        logger.info(f"Uploaded file saved to {file_path}")
    except Exception as e:
        logger.error(f"Failed to write file {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail="Could not save uploaded file.")
    
    # Initialize job in-memory db with UPLOADED status
    jobs_db[job_id] = {
        "job_id": job_id,
        "status": JobStatus.UPLOADED,
        "file_name": file.filename,
        "filename": file.filename,  # Matching the exact stored state key request
        "created_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "error_message": None,
        "study_pack": None,
        "pdf_url": None,
        "extracted_text_length": 0,
        "extracted_asset_count": 0,
        "assets": [],
        "pdf_file": None,
        "ocr_used": False
    }
    
    # Queue background task
    background_tasks.add_task(run_pdf_extraction_pipeline, job_id, file_path, file.filename)
    
    return UploadResponse(
        job_id=job_id,
        message="File uploaded successfully. Extraction pipeline started.",
        status=JobStatus.UPLOADED
    )
