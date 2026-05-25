import sys
import os
import uuid
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent
sys.path.append(str(backend_dir))

from app.config import settings
from app.utils.jobs_store import jobs_db
from app.models.schemas import ProductMode, JobStatus
from app.routes.upload import run_pdf_extraction_pipeline

def run_test():
    print("=== STARTING E2E VERIFICATION ===")
    
    # 1. Setup paths to real uploaded notes & question bank
    study_file = backend_dir / "test_study_material.docx"
    qb_file = backend_dir / "test_question_bank.docx"
    
    if not study_file.exists() or not qb_file.exists():
        print(f"ERROR: Verification files not found at:\n- {study_file}\n- {qb_file}")
        sys.exit(1)
        
    print(f"Found study material: {study_file}")
    print(f"Found question bank: {qb_file}")
    
    # Create unique job ID
    job_id = str(uuid.uuid4())
    jobs_db[job_id] = {
        "status": JobStatus.UPLOADED,
        "ocr_used": False
    }
    
    # Create upload directories if not exist
    settings.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    settings.ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    
    print("\n--- TEST 1: Normal Run (Primary models: Flash Lite) ---")
    print(f"QUESTION_PARSER_MODEL: {settings.QUESTION_PARSER_MODEL}")
    print(f"ANSWER_PACK_MODEL: {settings.ANSWER_PACK_MODEL}")
    print(f"STUDY_PACK_MODEL: {settings.STUDY_PACK_MODEL}")
    print(f"ANSWER_PACK_BATCH_SIZE: {settings.ANSWER_PACK_BATCH_SIZE}")
    print(f"MAX_ANSWER_PACK_CONTEXT_CHARS: {settings.MAX_ANSWER_PACK_CONTEXT_CHARS}")
    
    try:
        run_pdf_extraction_pipeline(
            job_id=job_id,
            study_file_paths=[str(study_file)],
            study_file_names=[study_file.name],
            question_bank_path=str(qb_file),
            question_bank_name=qb_file.name,
            mode=ProductMode.ANSWER_PACK
        )
        
        job_result = jobs_db[job_id]
        if job_result["status"] == JobStatus.COMPLETED:
            print("SUCCESS: Normal run completed successfully!")
            print(f"Generated PDF file: {job_result.get('pdf_file')}")
            print(f"Extracted text length: {job_result.get('extracted_text_length')} characters")
            print(f"Total solved questions: {len(job_result.get('answer_pack', {}).get('questions', []))}")
        else:
            print(f"FAILURE: Normal run status is {job_result['status']}.")
            print(f"Error Message: {job_result.get('error_message')}")
            sys.exit(1)
            
    except Exception as e:
        print(f"EXCEPTION in Normal Run: {str(e)}")
        sys.exit(1)
        
    print("\n--- TEST 2: Fallback Run (Mocking primary model failure) ---")
    # Temporarily set primary answer pack model to an invalid name to force fallback to gemini-2.5-flash
    original_model = settings.ANSWER_PACK_MODEL
    settings.ANSWER_PACK_MODEL = "gemini-invalid-model-name-mock"
    print(f"Set ANSWER_PACK_MODEL = '{settings.ANSWER_PACK_MODEL}' (forcing failure)")
    print(f"Set ANSWER_PACK_FALLBACK_MODEL = '{settings.ANSWER_PACK_FALLBACK_MODEL}' (expected recovery)")
    
    fallback_job_id = str(uuid.uuid4())
    jobs_db[fallback_job_id] = {
        "status": JobStatus.UPLOADED,
        "ocr_used": False
    }
    
    try:
        run_pdf_extraction_pipeline(
            job_id=fallback_job_id,
            study_file_paths=[str(study_file)],
            study_file_names=[study_file.name],
            question_bank_path=str(qb_file),
            question_bank_name=qb_file.name,
            mode=ProductMode.ANSWER_PACK
        )
        
        fallback_result = jobs_db[fallback_job_id]
        if fallback_result["status"] == JobStatus.COMPLETED:
            print("SUCCESS: Fallback recovery completed successfully!")
            print(f"Generated PDF file: {fallback_result.get('pdf_file')}")
            print(f"Total solved questions: {len(fallback_result.get('answer_pack', {}).get('questions', []))}")
        else:
            print(f"FAILURE: Fallback run status is {fallback_result['status']}.")
            print(f"Error Message: {fallback_result.get('error_message')}")
            sys.exit(1)
            
    except Exception as e:
        print(f"EXCEPTION in Fallback Run: {str(e)}")
        sys.exit(1)
    finally:
        # Restore settings
        settings.ANSWER_PACK_MODEL = original_model
        
    print("\n=== ALL E2E VERIFICATION TESTS PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    run_test()
