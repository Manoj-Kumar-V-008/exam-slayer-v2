import os
from pathlib import Path
from typing import Set
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory of the backend (i.e. exam-slayer-v2/backend)
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "Exam Slayer V2"
    API_V1_STR: str = "/api/v1"
    
    # Environment configs
    GEMINI_API_KEY: str = ""
    DEBUG: bool = True
    
    # Directories (resolved absolute paths)
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    ASSETS_DIR: Path = BASE_DIR / "assets"
    OUTPUTS_DIR: Path = BASE_DIR / "outputs"
    TEMPLATES_DIR: Path = BASE_DIR / "app" / "templates"
    
    # Allowed formats
    ALLOWED_EXTENSIONS: Set[str] = {
        "pdf",
        "docx",
        "doc",
        "pptx",
        "ppt",
        "jpg",
        "jpeg",
        "png"
    }
    
    # OCR fallback configuration
    OCR_THRESHOLD: int = 300
    OCR_MAX_PAGES: int = 20
    TESSERACT_CMD: str = ""
    
    # Run configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    FILE_RETENTION_HOURS: int = 24

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
