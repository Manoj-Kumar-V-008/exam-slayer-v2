from typing import Dict, Any

# Simple in-memory global dictionary to track processing jobs.
# Format: { job_id (str): job_details (dict) }
jobs_db: Dict[str, Any] = {}
