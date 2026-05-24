from fastapi import APIRouter, HTTPException
from app.models.schemas import JobResponse
from app.utils.jobs_store import jobs_db
from app.utils.logger import logger

router = APIRouter(prefix="/jobs", tags=["Jobs"])

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
        file_name=job_info["file_name"],
        created_at=job_info["created_at"],
        completed_at=job_info["completed_at"],
        error_message=job_info["error_message"],
        study_pack=job_info["study_pack"],
        pdf_url=job_info["pdf_url"],
        filename=job_info.get("filename"),
        extracted_text_length=job_info.get("extracted_text_length"),
        extracted_asset_count=job_info.get("extracted_asset_count"),
        assets=job_info.get("assets"),
        pdf_file=job_info.get("pdf_file"),
        ocr_used=job_info.get("ocr_used", False)
    )
