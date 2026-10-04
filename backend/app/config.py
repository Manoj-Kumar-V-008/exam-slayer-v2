import os
from pathlib import Path
from typing import Set, Any
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory of the backend (i.e. exam-slayer-v2/backend)
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "Exam Slayer V2"
    API_V1_STR: str = "/api/v1"
    
    # Environment configs
    GEMINI_API_KEY: str = ""
    DEBUG: bool = True
    
    # Gemini Model and Routing Configs (ordered prioritised lists)
    # NOTE (Oct 2026): gemini-2.5-* returns 404 for keys without prior usage
    # ("no longer available to new users") and "gemini-3-flash-preview" is not
    # a servable ID. Keep only actively-served 3.x IDs first, 2.5 last.
    QUESTION_PARSER_MODELS: list[str] = [
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-2.5-flash-lite"
    ]
    ANSWER_PACK_MODELS: list[str] = [
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash",
        "gemini-2.5-flash-lite"
    ]
    STUDY_PACK_MODELS: list[str] = [
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-2.5-flash"
    ]

    @field_validator("QUESTION_PARSER_MODELS", "ANSWER_PACK_MODELS", "STUDY_PACK_MODELS", mode="before")
    @classmethod
    def validate_model_list(cls, v: Any) -> list[str]:
        import json
        if isinstance(v, list):
            return [str(item).strip() for item in v if item]
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            # Try JSON array parsing first
            if v.startswith('[') and v.endswith(']'):
                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if item]
                except Exception:
                    pass
            # Fallback to comma-separated values
            return [item.strip() for item in v.split(',') if item.strip()]
        return []


    # Batching and Context Limits
    ANSWER_PACK_BATCH_SIZE: int = 2
    MAX_ANSWER_PACK_CONTEXT_CHARS: int = 40000
    
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
