from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.models.schemas import JobResponse
from app.utils.jobs_store import jobs_db
from app.utils.logger import logger
from app.config import settings

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.get("/download/{job_id}")
async def download_job_pdf(job_id: str):
    """Serve the compiled PDF file for a specific job ID."""
    if job_id not in jobs_db:
        logger.warning(f"Download failed: Job ID {job_id} not found in database.")
        raise HTTPException(status_code=404, detail="Job not found.")
        
    job_info = jobs_db[job_id]
    if job_info.get("status") != "completed":
        logger.warning(f"Download failed: Job ID {job_id} is not completed (status: {job_info.get('status')}).")
        raise HTTPException(status_code=400, detail="Solved PDF is not ready yet.")
        
    pdf_filename = job_info.get("pdf_file")
    if not pdf_filename:
        logger.warning(f"Download failed: Job ID {job_id} does not have a PDF filename registered.")
        raise HTTPException(status_code=404, detail="PDF filename not found.")
        
    pdf_path = settings.OUTPUTS_DIR / pdf_filename
    if not pdf_path.exists():
        logger.error(f"Download failed: Compiled PDF {pdf_path} does not exist on filesystem.")
        raise HTTPException(status_code=404, detail="Compiled PDF file not found on disk.")
        
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=pdf_filename
    )

@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """Retrieve the current processing status and output schema of a specific job ID."""
    if job_id not in jobs_db:
        logger.warning(f"Status check failed: Job ID {job_id} not found.")
        raise HTTPException(status_code=404, detail="Job not found.")
    
    job_info = jobs_db[job_id]
    return JobResponse(
        job_id=job_info["job_id"],
        status=job_info["status"],
        mode=job_info["mode"],
        file_name=job_info.get("file_name"),
        study_file_names=job_info.get("study_file_names", []),
        question_bank_name=job_info.get("question_bank_name"),
        study_file_count=job_info.get("study_file_count", 0),
        created_at=job_info["created_at"],
        completed_at=job_info["completed_at"],
        error_message=job_info["error_message"],
        study_pack=job_info.get("study_pack"),
        answer_pack=job_info.get("answer_pack"),
        pdf_url=job_info["pdf_url"],
        image_metadata=job_info.get("image_metadata"),
        filename=job_info.get("filename"),
        extracted_text_length=job_info.get("extracted_text_length"),
        extracted_asset_count=job_info.get("extracted_asset_count"),
        assets=job_info.get("assets"),
        pdf_file=job_info.get("pdf_file"),
        ocr_used=job_info.get("ocr_used", False)
    )
