import sys
import os
import time
import subprocess
import requests
from pathlib import Path

# Ensure backend directory is in path
backend_dir = Path(__file__).resolve().parent
sys.path.append(str(backend_dir))

def run_dist_validation():
    print("=== RUNNING LOCAL SPA DIST ROUTING VALIDATION ===")
    
    dist_dir = backend_dir.parent / "frontend" / "dist"
    if not dist_dir.exists():
        print(f"ERROR: Compiled frontend build not found at {dist_dir}")
        sys.exit(1)
        
    print(f"Found compiled frontend dist folder at: {dist_dir}")
    
    # Start the backend server
    print("Starting backend Uvicorn server...")
    server_log_path = backend_dir / "outputs" / "uvicorn_spa_validation.log"
    server_log_path.parent.mkdir(parents=True, exist_ok=True)
    server_log_file = open(server_log_path, "w", encoding="utf-8")
    
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000", "--host", "127.0.0.1"],
        stdout=server_log_file,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # Wait for the server to boot
    server_started = False
    print("Waiting for server to respond...")
    for i in range(15):
        try:
            res = requests.get("http://127.0.0.1:8000/api/v1/health", timeout=2)
            if res.status_code == 200:
                print("Server is healthy!")
                server_started = True
                break
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
        
    if not server_started:
        print("ERROR: Uvicorn server failed to start.")
        server_process.terminate()
        server_process.wait()
        server_log_file.close()
        sys.exit(1)
        
    try:
        # Verify 1: Fetching root "/" serves the React SPA index.html
        print("\n[TEST 1] Verifying SPA index serving...")
        root_res = requests.get("http://127.0.0.1:8000/")
        if root_res.status_code == 200 and "<div id=\"root\">" in root_res.text:
            print("SUCCESS: Root URL successfully served index.html!")
        else:
            print(f"FAILURE: Root URL returned status {root_res.status_code}. Response: {root_res.text[:300]}")
            stop_and_fail(server_process, server_log_file)
            
        # Verify 2: Catch-all client-side router fallback
        print("\n[TEST 2] Verifying client-side SPA routing fallback...")
        route_res = requests.get("http://127.0.0.1:8000/dashboard/jobs")
        if route_res.status_code == 200 and "<div id=\"root\">" in route_res.text:
            print("SUCCESS: Non-API route successfully fell back to serve index.html!")
        else:
            print(f"FAILURE: Client-side routing fallback failed. Status: {route_res.status_code}")
            stop_and_fail(server_process, server_log_file)
            
        # Verify 3: API routes still work correctly and are NOT caught by catch-all
        print("\n[TEST 3] Verifying API route integrity...")
        api_res = requests.get("http://127.0.0.1:8000/api/v1/health")
        if api_res.status_code == 200 and api_res.json().get("status") == "healthy":
            print("SUCCESS: API routes remain fully functional and unhindered by SPA router!")
        else:
            print(f"FAILURE: API route failed. Status: {api_res.status_code}. Response: {api_res.text}")
            stop_and_fail(server_process, server_log_file)
            
        print("\n=== ALL ROUTING TESTS PASSED SUCCESSFULLY! ===")
        print("Single-container SPA + API routing works flawlessly.")
        
        # Stop server
        server_process.terminate()
        server_process.wait()
        server_log_file.close()
        
    except Exception as ex:
        print(f"EXCEPTION in validation: {str(ex)}")
        stop_and_fail(server_process, server_log_file)

def stop_and_fail(process, log_file):
    try:
        process.terminate()
        process.wait(timeout=5)
    except:
        process.kill()
    try:
        log_file.close()
    except:
        pass
    sys.exit(1)

if __name__ == "__main__":
    run_dist_validation()
