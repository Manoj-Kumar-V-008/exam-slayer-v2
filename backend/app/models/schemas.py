from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator

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

class ProductMode(str, Enum):
    STUDY_PACK = "STUDY_PACK"
    ANSWER_PACK = "ANSWER_PACK"

class SolvedQuestion(BaseModel):
    question_number: str = Field(..., description="The numbering or label of the question (e.g. 'Question 1', 'Question 2(a)').")
    question_text: str = Field(..., description="The full wording of the question extracted from the question bank.")
    marks_category: Optional[str] = Field(None, description="The estimated or explicit marks category (e.g. '2 Marks', '5 Marks', '10 Marks').")
    dominant_intent: Optional[str] = Field(None, description="The dominant intent (primary focus) of the question.")
    sub_intents: List[str] = Field(default_factory=list, description="A list of all sub-intents detected in the question.")
    answer: str = Field("", description="The comprehensive, exam-ready answer. Strict Word Counts: 2 Marks = 80-150 words; 5 Marks = 200-350 words; 10 Marks = 450-800 words. You MUST expand using domain knowledge to meet these limits. Formatting by type: 'theory' (intro, multi-level structured explanation, examples, mnemonics, quick revision summary); 'sql' (```sql code block -> detailed line explanation -> column meaning); 'er_model' (schemas with underlined PK/italic FK, mapping steps, keys); 'comparison' (clean markdown table comparing metrics); 'problem_solving' (clear step-by-step math/logic).")
    simple_explanation: str = Field(..., description="A simple background analogy or high-level summary, strictly under 50 words.")
    quick_revision_points: List[str] = Field(default_factory=list, description="Exactly 3 short bullet points, strictly under 8 words per bullet, summarizing key takeaways.")
    memory_trick: Optional[str] = Field(None, description="A memory aid (mnemonic, acronym, etc.) to help remember this answer, strictly under 12 words.")
    related_assets: List[str] = Field(default_factory=list, description="Filename pointers of any diagrams/graphics from study materials relevant to this question.")



class AnswerPack(BaseModel):
    title: str = Field(..., description="The main subject or title of the answer pack.")
    questions: List[SolvedQuestion] = Field(..., description="The list of solved questions.")

class Section(BaseModel):
    heading: str = Field(..., description="The main heading for this topic section.")
    summary: str = Field(..., description="A concise, high-level summary of the concept.")
    simple_explanation: str = Field(..., description="An intuitive explanation or plain-English analogy of the concept.")
    key_points: List[str] = Field(default_factory=list, description="Key bullet points for core learning.")
    exam_tip: Optional[str] = Field(None, description="Tip/advice for exams, pitfalls, or trap alerts.")
    likely_questions_2_marks: List[str] = Field(default_factory=list, description="Likely short-answer questions (2 marks).")
    likely_questions_5_marks: List[str] = Field(default_factory=list, description="Likely medium-length questions (5 marks).")
    likely_questions_10_marks: List[str] = Field(default_factory=list, description="Likely essay/long questions (10 marks).")
    common_mistakes: List[str] = Field(default_factory=list, description="Common student mistakes or misunderstandings.")
    memory_trick: Optional[str] = Field(None, description="Memory aid (mnemonic, acronym, etc.) to help remember this concept.")
    revision_cheatsheet: List[str] = Field(default_factory=list, description="Short summary/bullet list for quick cheatsheet review.")
    embedded_assets: List[str] = Field(default_factory=list, description="Diagram filenames from study notes relevant to this section.")

class StudyPack(BaseModel):
    title: str = Field(..., description="The overall title of the study pack guide.")
    sections: List[Section] = Field(..., description="List of topic sections in the study pack.")

class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    mode: ProductMode
    file_name: Optional[str] = None
    study_file_names: List[str] = Field(default_factory=list)
    question_bank_name: Optional[str] = None
    study_file_count: int = 0
    created_at: str
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    study_pack: Optional[StudyPack] = None
    answer_pack: Optional[AnswerPack] = None
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
    mode: ProductMode

class HealthCheckResponse(BaseModel):
    status: str
    project: str
    debug_mode: bool
