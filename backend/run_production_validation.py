import sys
import os
import time
import subprocess
import requests
from pathlib import Path

# Ensure backend directory is in path
backend_dir = Path(__file__).resolve().parent
sys.path.append(str(backend_dir))

def run_production_validation():
    print("=== STARTING REAL PRODUCTION VALIDATION ===")
    
    study_file = backend_dir / "test_study_material.docx"
    qb_file = backend_dir / "test_question_bank.docx"
    
    if not study_file.exists() or not qb_file.exists():
        print(f"ERROR: Real files not found at {backend_dir}")
        sys.exit(1)
        
    # Start the backend server
    print("Starting backend Uvicorn server...")
    log_dir = backend_dir / "outputs"
    log_dir.mkdir(parents=True, exist_ok=True)
    server_log_path = log_dir / "uvicorn_server.log"
    server_log_file = open(server_log_path, "w", encoding="utf-8")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000", "--host", "127.0.0.1"],
        stdout=server_log_file,
        stderr=subprocess.STDOUT,  # Redirect stderr to stdout log file
        text=True
    )
    
    # Wait for the health check to respond
    health_url = "http://127.0.0.1:8000/api/v1/health"
    server_started = False
    print("Waiting for server to become healthy...")
    for i in range(30):
        try:
            res = requests.get(health_url, timeout=2)
            if res.status_code == 200:
                print(f"Server is healthy! Status: {res.json()}")
                server_started = True
                break
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
        
    if not server_started:
        print("ERROR: Uvicorn server failed to start in 30 seconds.")
        server_process.terminate()
        server_process.wait()
        server_log_file.close()
        with open(server_log_path, "r", encoding="utf-8") as f:
            stdout = f.read()
        print(f"Server output:\n{stdout}")
        sys.exit(1)
        
    # Run the upload request
    upload_url = "http://127.0.0.1:8000/api/v1/upload"
    print("\nTriggering E2E upload flow via HTTP POST...")
    start_time = time.time()
    
    files = [
        ("study_files", (study_file.name, open(study_file, "rb"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
        ("question_bank", (qb_file.name, open(qb_file, "rb"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))
    ]
    data = {
        "mode": "ANSWER_PACK"
    }
    
    try:
        response = requests.post(upload_url, files=files, data=data)
        if response.status_code != 200:
            print(f"ERROR: Upload failed with status code {response.status_code}")
            print(f"Response: {response.text}")
            stop_server(server_process)
            sys.exit(1)
            
        upload_data = response.json()
        job_id = upload_data.get("job_id")
        print(f"Upload successful. Job ID: {job_id}")
        
        # Poll the job status endpoint
        job_url = f"http://127.0.0.1:8000/api/v1/jobs/{job_id}"
        print("Polling job status...")
        
        completed = False
        duration = 0
        
        while True:
            time.sleep(5)
            job_res = requests.get(job_url)
            if job_res.status_code != 200:
                print(f"ERROR: Failed to poll job. Status code: {job_res.status_code}")
                stop_server(server_process)
                sys.exit(1)
                
            job_info = job_res.json()
            status = job_info.get("status")
            print(f"Job status: {status}")
            
            if status == "completed":
                completed = True
                duration = time.time() - start_time
                print("\nJob completed successfully!")
                break
            elif status == "failed":
                print(f"\nJob failed. Error: {job_info.get('error_message')}")
                break
                
        # 1. Download and verify PDF BEFORE shutting down the server
        pdf_valid = False
        page_count = 0
        pdf_filename = None
        
        if completed:
            download_url = f"http://127.0.0.1:8000/api/v1/jobs/download/{job_id}"
            print(f"Downloading final PDF from: {download_url}...")
            try:
                download_res = requests.get(download_url)
                if download_res.status_code == 200:
                    pdf_filename = f"prod_validation_{job_id}.pdf"
                    pdf_path = backend_dir / "outputs" / pdf_filename
                    with open(pdf_path, "wb") as f:
                        f.write(download_res.content)
                    
                    import fitz
                    doc = fitz.open(str(pdf_path))
                    page_count = len(doc)
                    doc.close()
                    pdf_valid = True
                    print(f"Downloaded PDF successfully. Size: {len(download_res.content)} bytes.")
                else:
                    print(f"ERROR: Download API failed with status code {download_res.status_code}")
            except Exception as dl_err:
                print(f"ERROR: Exception during download: {str(dl_err)}")

        # 2. Terminate server and read all output logs
        print("\nStopping server and reading logs...")
        server_process.terminate()
        server_process.wait()
        server_log_file.close()
        
        # Read logs from file
        with open(server_log_path, "r", encoding="utf-8") as f:
            stdout = f.read()
        
        # Parse logs for verification details
        log_lines = stdout.splitlines()
        
        # API Calls Tracking
        gemini_calls = []
        fallbacks_triggered = []
        splits_triggered = []
        quota_failures = []
        
        for line in log_lines:
            if "Generating content with model" in line:
                # Find model name in log line
                import re
                match = re.search(r"model '([^']+)'", line)
                if match:
                    gemini_calls.append(match.group(1))
            if "Switching immediately to fallback model" in line:
                match = re.search(r"fallback model '([^']+)'", line)
                if match:
                    fallbacks_triggered.append(match.group(1))
            if "Dynamically reducing batch size" in line:
                splits_triggered.append(line)
            if "429" in line or "quota" in line.lower() or "resource_exhausted" in line.lower():
                quota_failures.append(line)
            
        print("\n" + "="*50)
        print("          PRODUCTION VALIDATION REPORT          ")
        print("="*50)
        print(f"Job ID: {job_id}")
        print(f"E2E Generation Duration: {duration:.2f} seconds")
        print(f"E2E Status: {'SUCCESS' if completed else 'FAILED'}")
        print(f"Success Criteria Met: {'YES' if (completed and pdf_valid) else 'NO'}")
        
        if completed:
            # Details from job info
            parsed_questions = len(job_info.get("answer_pack", {}).get("questions", []))
            print(f"Exact parsed question count: {parsed_questions}")
            print(f"Generated PDF File: {pdf_filename}")
            print(f"Final PDF Page Count: {page_count}")
        else:
            print("ERROR: Pipeline did not complete successfully.")
            
        print("\n--- Gemini API Quota Telemetry ---")
        print(f"Total Gemini API calls made: {len(gemini_calls)}")
        for idx, model in enumerate(gemini_calls, 1):
            print(f"  Call {idx}: Model '{model}'")
            
        print(f"Fallback switches triggered: {len(fallbacks_triggered)}")
        for fallback in fallbacks_triggered:
            print(f"  - Switched to fallback: '{fallback}'")
            
        print(f"Dynamic batch splits triggered: {len(splits_triggered)}")
        print(f"Quota exhaustion (429) events: {len(quota_failures)}")
        print(f"Flash-Lite model succeeded: {'YES' if 'gemini-2.5-flash-lite' in gemini_calls else 'N/A'}")
        print(f"Premium Flash model fallback triggered: {'YES' if len(fallbacks_triggered) > 0 else 'NO'}")
        
        print("="*50)
        
        if not completed or not pdf_valid:
            print("\nFull Server Log for debugging:\n")
            print(stdout)
            sys.exit(1)
            
    except Exception as ex:
        print(f"\nEXCEPTION in production validation: {str(ex)}")
        stop_server(server_process)
        sys.exit(1)

def stop_server(process):
    try:
        process.terminate()
        process.wait(timeout=5)
    except Exception:
        process.kill()

if __name__ == "__main__":
    run_production_validation()
