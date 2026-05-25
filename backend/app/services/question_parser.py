import json
import time
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from app.config import settings
from app.utils.logger import logger
from app.services.ai import generate_content_with_fallback

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
1. Detect and extract Top-Level Questions ONLY:
   - Identify top-level questions by their main numbering (e.g., "Question 1", "Question 2", "1.", "2.").
   - Do NOT create separate entries for sub-questions or multipart divisions (e.g., "Question 4(a)", "Question 4(b)", "4a", "4b").
2. Preserve multipart sub-questions inside the parent question:
   - Keep all subparts, options, and lists (e.g., "a)", "b)", "c)", "d)", "i)", "ii)", "1)", "2)") attached inside the parent question's `question_text` field.
   - For example, if Question 4 has parts a, b, c, and d, extract it as a single question with `question_number = "Question 4"` (or "4") and format the subparts inside the `question_text` as part of the question text.
3. Do NOT split schema instruction blocks, table structures, metadata headings, or schema titles into separate questions. Only extract actual questions to be solved.
4. Handle OR Choices:
   - Example: "Answer Q3 OR Q4".
   - If Q3 and Q4 are separate top-level questions, extract BOTH as separate top-level questions.
5. Filter OCR Noise & Metadata:
   - Filter out page numbers, headers, footers, and general OCR artifacts.
   - Filter out instructions like "Time: 3 hours", "Answer any 5 questions", or "Marks will be awarded for clean code". Only extract actual questions to solve.
6. Extract/Infer Marks:
   - Look for explicit marks indications in the text (e.g., "[10 marks]", "(5m)", "2 marks"). Keep the clean text like "2 Marks", "5 Marks", "10 Marks".
   - If marks are not explicitly stated, infer the weight based on the question length, complexity, and verbs used (e.g., "Define" is likely 2 Marks; "Explain" or "Discuss" is likely 5 Marks; "Design", "Derive", "Detail", or essay questions are likely 10 Marks).
7. Extremely Aggressive Semantic De-duplication & Consolidation (Target 18-22 Questions):
   - You MUST aggressively group and merge questions that are semantically overlapping, asking for the same core concept/definition, or have similar exercises. College question banks repeat the same concepts multiple times with minor wording changes.
   - For example:
     * Merge all variations of "DBMS vs Traditional File Systems" and "Advantages of DBMS" into a single comprehensive question.
     * Merge all variations of "Three-schema architecture" and "logical/physical data independence" into a single question.
     * Merge all variations of "Database users" and "types of end users" into a single question.
     * Merge all variations of "SQL Views" and view creation exercises into a single question.
     * Merge all variations of "Weak entity vs Strong entity" and definitions of ER terms (keys, attributes, recursive relationships) into a single consolidated terms definition question.
     * Merge duplicate Relational Algebra schema questions or exercises if they are identical or ask for similar retrievals.
   - If a topic/concept is covered by another question in the list, discard the duplicate/redundant question. Ensure the remaining question is broad enough to cover it.
   - The final output MUST contain only 18 to 22 unique, high-density main questions. Do NOT exceed 22 questions.

RAW QUESTION BANK TEXT:
{raw_qb_text}
"""

    try:
        parsed_data = generate_content_with_fallback(
            prompt=prompt,
            response_schema=ParsedQuestionList,
            primary_model=settings.QUESTION_PARSER_MODEL,
            fallback_model=settings.QUESTION_PARSER_FALLBACK_MODEL,
            temperature=0.1
        )
        logger.info(f"Successfully extracted {len(parsed_data.questions)} questions from question bank.")
        return [q.model_dump() for q in parsed_data.questions]
    except Exception as e:
        logger.error(f"Failed to parse questions from question bank: {str(e)}")
        raise RuntimeError(f"Failed to parse questions from question bank: {str(e)}") from e
