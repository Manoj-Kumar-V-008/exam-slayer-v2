import os
import time
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes import upload, jobs
from app.models.schemas import HealthCheckResponse
from app.utils.logger import logger

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for compiling mess educational materials into clean premium study packs.",
    version="2.0.0"
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adapt to specific React dev ports in production config
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def cleanup_old_files():
    """Deletes generated files and directories older than the configured retention window."""
    import shutil
    retention_hours = settings.FILE_RETENTION_HOURS
    if retention_hours <= 0:
        logger.warning("Skipping file cleanup because FILE_RETENTION_HOURS is not positive.")
        return

    cutoff_timestamp = time.time() - (retention_hours * 3600)
    cleanup_dirs = [
        settings.ASSETS_DIR,
        settings.OUTPUTS_DIR
    ]

    deleted_count = 0
    
    # 1. Clean assets and outputs files
    for folder in cleanup_dirs:
        if not folder.exists():
            continue

        for path in folder.rglob("*"):
            try:
                if not path.is_file():
                    continue

                if path.stat().st_mtime < cutoff_timestamp:
                    path.unlink()
                    deleted_count += 1
                    logger.info(f"Deleted expired file during startup cleanup: {path}")
            except Exception as e:
                logger.error(f"Failed to clean up file {path}: {str(e)}")

    # 2. Clean upload folders recursively
    if settings.UPLOAD_DIR.exists():
        for path in settings.UPLOAD_DIR.iterdir():
            try:
                if path.stat().st_mtime < cutoff_timestamp:
                    if path.is_file():
                        path.unlink()
                        deleted_count += 1
                        logger.info(f"Deleted expired upload file: {path}")
                    elif path.is_dir():
                        shutil.rmtree(path)
                        deleted_count += 1
                        logger.info(f"Deleted expired upload folder recursively: {path}")
            except Exception as e:
                logger.error(f"Failed to clean up upload path {path}: {str(e)}")

    logger.info(
        f"Startup file cleanup complete. Deleted {deleted_count} file(s)/folder(s) older than "
        f"{retention_hours} hour(s)."
    )

# Startup events
@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Exam Slayer V2 FastAPI server...")
    
    # Generate required folders automatically on start
    folders_to_create = [
        settings.UPLOAD_DIR,
        settings.ASSETS_DIR,
        settings.OUTPUTS_DIR,
        settings.TEMPLATES_DIR
    ]
    
    for folder in folders_to_create:
        try:
            folder.mkdir(parents=True, exist_ok=True)
            logger.info(f"Verified directory exists: {folder}")
        except Exception as e:
            logger.error(f"Error creating directory {folder}: {str(e)}")

    import threading
    threading.Thread(target=cleanup_old_files, daemon=True).start()

# Health check route
@app.post(f"{settings.API_V1_STR}/health", response_model=HealthCheckResponse, tags=["Health"])
@app.get(f"{settings.API_V1_STR}/health", response_model=HealthCheckResponse, tags=["Health"])
async def health_check():
    return HealthCheckResponse(
        status="healthy",
        project=settings.PROJECT_NAME,
        debug_mode=settings.DEBUG
    )

app.include_router(upload.router, prefix=settings.API_V1_STR)
app.include_router(jobs.router, prefix=settings.API_V1_STR)

# Serve backend extracted assets (images) via HTTP
app.mount("/backend-assets", StaticFiles(directory=str(settings.ASSETS_DIR)), name="backend-assets")

# Serve built frontend static files if the dist folder exists (checks both Docker and local dev structures)
dist_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if not dist_dir.exists():
    dist_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if dist_dir.exists():
    # Mount static assets (js, css, images)
    assets_dir = dist_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    
    @app.get("/favicon.ico", include_in_schema=False)
    async def get_favicon_ico():
        from fastapi import HTTPException
        ico_path = dist_dir / "favicon.ico"
        if ico_path.exists():
            return FileResponse(str(ico_path))
        png_path = dist_dir / "favicon.png"
        if png_path.exists():
            return FileResponse(str(png_path))
        raise HTTPException(status_code=404, detail="Favicon not found")

    @app.get("/favicon.png", include_in_schema=False)
    async def get_favicon_png():
        from fastapi import HTTPException
        png_path = dist_dir / "favicon.png"
        if png_path.exists():
            return FileResponse(str(png_path))
        raise HTTPException(status_code=404, detail="Favicon not found")

    @app.get("/")
    async def serve_root():
        return FileResponse(str(dist_dir / "index.html"))
    
    # Catch-all route to serve the React SPA index.html for non-API routes
    @app.get("/{catchall:path}")
    async def serve_spa(catchall: str):
        # Prevent catching API routes
        if catchall.startswith("api/") or catchall.startswith("api/v1"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="API route not found")
            
        # If it's a specific file inside dist (like favicon.ico, logo.png), serve it
        file_path = dist_dir / catchall
        if file_path.is_file():
            return FileResponse(file_path)
        # Fall back to index.html for SPA routing
        return FileResponse(str(dist_dir / "index.html"))

