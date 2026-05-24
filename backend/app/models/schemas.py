from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    OCR_PROCESSING = "ocr_processing"
    AI_PROCESSING = "ai_processing"
    PDF_GENERATING = "pdf_generating"
    COMPLETED = "completed"
    FAILED = "failed"

class Section(BaseModel):
    heading: str = Field(..., description="The heading of this study section.")
    summary: str = Field(..., description="Detailed content summary of the topic.")
    simple_explanation: str = Field(..., description="A simple, intuitive explanation of the concept using analogies or everyday examples.")
    key_points: List[str] = Field(default_factory=list, description="A list of key concepts, formulas, or facts to remember.")
    exam_tip: Optional[str] = Field(None, description="An essential note or hint to help students excel in exams.")
    likely_questions_2_marks: List[str] = Field(default_factory=list, description="Likely short-answer 2-mark exam questions on this topic.")
    likely_questions_5_marks: List[str] = Field(default_factory=list, description="Likely medium-answer 5-mark exam questions on this topic.")
    likely_questions_10_marks: List[str] = Field(default_factory=list, description="Likely essay-style or computational 10-mark exam questions on this topic.")
    common_mistakes: List[str] = Field(default_factory=list, description="Common mistakes students make when answering questions on this topic.")
    memory_trick: Optional[str] = Field(None, description="A mnemonic, acronym, or memory trick to remember key terms or concepts.")
    revision_cheatsheet: List[str] = Field(default_factory=list, description="Quick summary points or checklists for fast revision right before the exam.")
    embedded_assets: List[str] = Field(default_factory=list, description="List of image/diagram filenames that should be rendered in this section (e.g. img_01.png).")

class StudyPack(BaseModel):
    title: str = Field(..., description="The main subject or overall title of the study guide.")
    sections: List[Section] = Field(..., description="The sections that comprise the study guide.")

class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    file_name: str
    created_at: str
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    study_pack: Optional[StudyPack] = None
    pdf_url: Optional[str] = None
    
    # Extraction pipeline metadata
    filename: Optional[str] = None
    extracted_text_length: Optional[int] = None
    extracted_asset_count: Optional[int] = None
    assets: Optional[List[str]] = None
    pdf_file: Optional[str] = None
    ocr_used: Optional[bool] = False

class UploadResponse(BaseModel):
    job_id: str
    message: str
    status: JobStatus

class HealthCheckResponse(BaseModel):
    status: str
    project: str
    debug_mode: bool
