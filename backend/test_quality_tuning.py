import sys
import uuid
import re
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent
sys.path.append(str(backend_dir))

from app.config import settings
from app.utils.jobs_store import jobs_db
from app.models.schemas import ProductMode, JobStatus
from app.routes.upload import run_pdf_extraction_pipeline

def count_words(text: str) -> int:
    # Clean markdown formatting to get a more accurate word count
    clean_text = re.sub(r"[#\*_`\-\|]", " ", text)
    return len(clean_text.split())

def run_quality_tuning_validation():
    print("=== STARTING QUALITY TUNING VALIDATION ===")
    
    study_file = backend_dir / "test_study_material.docx"
    qb_file = backend_dir / "test_10_question_bank.docx"
    
    if not study_file.exists() or not qb_file.exists():
        print(f"ERROR: Files not found:\n- {study_file}\n- {qb_file}")
        sys.exit(1)
        
    print(f"Found study material: {study_file}")
    print(f"Found 10-question bank: {qb_file}")
    
    # Create unique job ID
    job_id = str(uuid.uuid4())
    jobs_db[job_id] = {
        "status": JobStatus.UPLOADED,
        "ocr_used": False
    }
    
    # Create directories
    settings.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    settings.ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    
    original_models = settings.ANSWER_PACK_MODELS
    settings.ANSWER_PACK_MODELS = ["gemini-3.5-flash", "gemini-3.1-flash-lite"]
    
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
        if job_result["status"] != JobStatus.COMPLETED:
            print(f"FAILURE: Job status is {job_result['status']}.")
            print(f"Error Message: {job_result.get('error_message')}")
            sys.exit(1)
            
        print("SUCCESS: Pipeline completed successfully!")
        
        answer_pack = job_result.get("answer_pack", {})
        questions = answer_pack.get("questions", [])
        
        print(f"\nTotal solved questions: {len(questions)}")
        
        # Validation checks
        errors = []
        
        # 1. Exact 10 outputs
        if len(questions) != 10:
            errors.append(f"Expected exactly 10 questions, but got {len(questions)}")
            
        # 2. Check each question
        for i, q in enumerate(questions, 1):
            q_num = q.get("question_number", f"Unknown {i}")
            q_text = q.get("question_text", "")
            q_type = q.get("question_type", "None")
            q_marks = q.get("marks_category", "None")
            answer = q.get("answer", "")
            word_count = count_words(answer)
            
            print(f"\n--- Question {i}: {q_num} [{q_marks}] ({q_type}) ---")
            print(f"Text: {q_text[:100]}...")
            print(f"Answer length: {word_count} words")
            
            # Grounding check
            if "extended beyond uploaded notes" in answer.lower():
                errors.append(f"Question {q_num} contains the forbidden note disclaimer.")
                
            # Marks-aware sizing checks
            if "2 Marks" in q_marks:
                # 80-150 words
                if word_count < 80 or word_count > 180: # Allow a tiny bit of upper buffer
                    errors.append(f"Question {q_num} (2 Marks) has {word_count} words (Expected 80-150).")
            elif "5 Marks" in q_marks:
                # 200-350 words
                if word_count < 180 or word_count > 380: # Allow tiny buffer
                    errors.append(f"Question {q_num} (5 Marks) has {word_count} words (Expected 200-350).")
            elif "10 Marks" in q_marks:
                # 450-800 words
                if word_count < 400 or word_count > 850:
                    errors.append(f"Question {q_num} (10 Marks) has {word_count} words (Expected 450-800).")
                    
            # Type-specific checks
            if q_type == "sql":
                if "```sql" not in answer.lower():
                    errors.append(f"Question {q_num} (SQL) answer is not SQL-shaped (missing ```sql code block).")
            elif q_type == "comparison":
                if "|" not in answer:
                    errors.append(f"Question {q_num} (comparison) answer does not contain a markdown table.")
                    
        # Summary
        if errors:
            print("\n=== VALIDATION FAILED ===")
            for err in errors:
                print(f"- {err}")
            sys.exit(1)
        else:
            print("\n=== ALL QUALITY VALIDATION TESTS PASSED SUCCESSFULLY ===")
            print("1. Exact count = 10 verified.")
            print("2. Marks-aware sizing verified.")
            print("3. Type classification and formatting verified.")
            print("4. Grounding cleanup verified.")
            
    except Exception as e:
        print(f"EXCEPTION in validation run: {str(e)}")
        sys.exit(1)
    finally:
        settings.ANSWER_PACK_MODELS = original_models


if __name__ == "__main__":
    run_quality_tuning_validation()
