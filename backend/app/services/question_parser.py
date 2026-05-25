import json
import time
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from app.config import settings
from app.utils.logger import logger
from app.services.ai import _is_transient_gemini_error, GEMINI_MAX_ATTEMPTS, GEMINI_RETRY_DELAYS_SECONDS

class ParsedQuestion(BaseModel):
    question_number: str = Field(..., description="The numbering or label of the question, e.g., 'Question 1', 'Question 2(a)'.")
    question_text: str = Field(..., description="The full wording of the question.")
    likely_marks: Optional[str] = Field(None, description="The estimated or explicit marks category, e.g. '2 Marks', '5 Marks', '10 Marks'.")

class ParsedQuestionList(BaseModel):
    questions: List[ParsedQuestion] = Field(..., description="The list of parsed questions.")

def parse_questions_from_bank(raw_qb_text: str) -> List[dict]:
    """
    Sends the raw text of the question bank to Gemini to parse and normalize into a structured
    list of individual questions, robustly handling numbering, sub-questions, OR choices,
    sections, and OCR noise.
    
    Args:
        raw_qb_text: The extracted raw text of the question bank document.
        
    Returns:
        A list of dictionaries matching the ParsedQuestion schema.
    """
    if not settings.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not configured in settings.")
        raise ValueError("Gemini API key is missing. Please configure GEMINI_API_KEY in your .env file.")
        
    if not raw_qb_text.strip():
        logger.warning("Empty raw question bank text provided for parsing.")
        return []
        
    logger.info("Parsing question bank text into structured questions...")
    
    prompt = f"""
You are an expert Exam Question Extractor and Normalizer.
Your goal is to parse raw text extracted from a College Question Bank, Homework sheet, or Past Year Questions (PYQ) document, and isolate every individual question.

CRITICAL PARSING RULES:
1. Isolate each question and sub-question:
   - Extract multipart sub-questions (e.g. "1a" and "1b", or "Question 2(i)" and "Question 2(ii)") as separate, individual entries in the list.
   - Maintain the original label prefixes so the student knows exactly which question is being solved (e.g., "Question 1(a)", "Question 1(b)").
2. Handle OR Choices:
   - Example: "Answer Q3 OR Q4".
   - Extract BOTH questions as separate individual entries (e.g., "Question 3" and "Question 4") so the student receives solutions for both options.
3. Handle Sections/Parts:
   - Prepend the section name to the question number if helpful (e.g. "Part A - Question 1").
4. Filter OCR Noise & Metadata:
   - Filter out page numbers, headers, footers, and general OCR artifacts.
   - Filter out instructions like "Time: 3 hours", "Answer any 5 questions", or "Marks will be awarded for clean code". Only extract actual questions to solve.
5. Extract/Infer Marks:
   - Look for explicit marks indications in the text (e.g., "[10 marks]", "(5m)", "2 marks"). Keep the clean text like "2 Marks", "5 Marks", "10 Marks".
   - If marks are not explicitly stated, infer the weight based on the question length, complexity, and verbs used (e.g., "Define" is likely 2 Marks; "Explain" or "Discuss" is likely 5 Marks; "Design", "Derive", "Detail", or essay questions are likely 10 Marks).

RAW QUESTION BANK TEXT:
{raw_qb_text}
"""

    last_error = None
    for attempt in range(1, GEMINI_MAX_ATTEMPTS + 1):
        try:
            logger.info(f"Gemini question parser attempt {attempt}/{GEMINI_MAX_ATTEMPTS}...")
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ParsedQuestionList,
                    temperature=0.1
                )
            )
            
            raw_response = response.text
            if not raw_response:
                raise ValueError("Received an empty response from Gemini question parser.")
                
            parsed_data = ParsedQuestionList.model_validate_json(raw_response)
            logger.info(f"Successfully extracted {len(parsed_data.questions)} questions from question bank.")
            return [q.model_dump() for q in parsed_data.questions]
            
        except Exception as e:
            last_error = e
            if _is_transient_gemini_error(e) and attempt < GEMINI_MAX_ATTEMPTS:
                delay = GEMINI_RETRY_DELAYS_SECONDS[attempt - 1]
                logger.warning(f"Transient error during question parsing: {str(e)}. Retrying in {delay}s...")
                time.sleep(delay)
                continue
                
            logger.error(f"Failed to parse questions from question bank: {str(e)}")
            raise RuntimeError(f"Failed to parse questions from question bank: {str(e)}") from e
            
    raise RuntimeError(f"Failed to parse questions from question bank after {GEMINI_MAX_ATTEMPTS} attempts: {str(last_error)}") from last_error
