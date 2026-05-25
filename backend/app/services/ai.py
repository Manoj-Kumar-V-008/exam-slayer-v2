import json
import time
from typing import List
from google import genai
from google.genai import types
from app.config import settings
from app.models.schemas import AnswerPack, StudyPack
from app.utils.logger import logger

GEMINI_MAX_ATTEMPTS = 3
GEMINI_RETRY_DELAYS_SECONDS = [10, 30]


def _is_transient_gemini_error(exc: Exception) -> bool:
    """Best-effort detection for retryable Gemini/API failures."""
    message = str(exc).lower()
    retry_markers = [
        "429",
        "quota",
        "rate limit",
        "rate-limit",
        "resource_exhausted",
        "too many requests",
        "timeout",
        "timed out",
        "temporarily unavailable",
        "unavailable",
        "503",
        "502",
        "500",
        "504",
    ]
    return any(marker in message for marker in retry_markers)


def clean_study_notes(raw_text: str) -> dict:
    """
    Sends raw extracted text to Gemini to structure into a student-friendly StudyPack guide.
    
    Args:
        raw_text: The layout-sorted extracted text with inline image placeholders.
        
    Returns:
        A dictionary matching the StudyPack schema format.
    """
    if not settings.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not configured in settings.")
        raise ValueError("Gemini API key is missing. Please configure GEMINI_API_KEY in your .env file.")
        
    logger.info("Sending content to Gemini for study pack guide generation...")
    
    prompt = f"""
You are an expert academic tutor, examiner, and content compiler. 
Your task is to convert raw extracted academic materials into a premium, clean, exam-ready study guide.

=== STUDY MATERIALS ===
{raw_text}

INSTRUCTIONS FOR GENERATION:
1. Organize the content into a cohesive, structured study guide.
2. For each section, provide a concise 'summary' of the core topic.
3. Write a 'simple_explanation' that explains the concept using clear, intuitive analogies or everyday examples, followed by details.
4. Keep the content technically correct and precise, but highly accessible.
5. Create lists of 'key_points' summarizing the facts, formulas, or rules.
6. Provide actionable 'exam_tip' notes highlighting what examiners look for or common traps.
7. Generate likely exam questions based on standard curriculum weightings:
   - 'likely_questions_2_marks': Short definition or identification questions.
   - 'likely_questions_5_marks': Medium-length explanations, comparisons, or procedures.
   - 'likely_questions_10_marks': Comprehensive essay, architecture, or deep computational questions.
8. Identify 'common_mistakes' that students typically make when writing answers for these topics (e.g. confusing terms, omitting steps).
9. Create a 'memory_trick' (like a mnemonic, acronym, or memory peg) to help students easily recall lists or complex concepts.
10. Draft a list of 'revision_cheatsheet' points—one-liners for quick revision right before entering the exam room.
11. FORMATTING RULES (Safe Markdown):
    - You are allowed and encouraged to use standard semantic markdown syntax in string fields to enhance readability and structure.
    - Do NOT use raw HTML.
    - Unicode math symbols, superscripts, subscripts, and greek letters (e.g. λ, theta, eigenvalues/eigenvectors symbols) should be preserved exactly as-is to maintain formula rendering quality.
12. CRITICAL ASSET RULES:
    - You must preserve all image/diagram asset placeholders from the raw text EXACTLY as they appear: {{{{IMAGE_ASSET:filename.png}}}}
    - Decide exactly which section it belongs to based on context, and place the filename (e.g. 'abc123_img_1.png') inside 'embedded_assets' list.

Return a structured JSON output conforming to the StudyPack schema.
"""

    last_error = None
    for attempt in range(1, GEMINI_MAX_ATTEMPTS + 1):
        try:
            logger.info(f"Gemini study guide generation attempt {attempt}/{GEMINI_MAX_ATTEMPTS}...")
            client = genai.Client(api_key=settings.GEMINI_API_KEY)

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=StudyPack,
                    temperature=0.2
                )
            )

            raw_response_text = response.text
            if not raw_response_text:
                raise ValueError("Received an empty response from Gemini API.")

            study_pack = StudyPack.model_validate_json(raw_response_text)
            logger.info(f"Successfully compiled study guide pack: '{study_pack.title}' with {len(study_pack.sections)} sections.")
            return study_pack.model_dump()

        except Exception as e:
            last_error = e
            if _is_transient_gemini_error(e) and attempt < GEMINI_MAX_ATTEMPTS:
                delay_seconds = GEMINI_RETRY_DELAYS_SECONDS[attempt - 1]
                logger.warning(f"Transient error during study guide generation: {str(e)}. Retrying in {delay_seconds}s...")
                time.sleep(delay_seconds)
                continue

            logger.error(f"Failed during study guide generation step: {str(e)}")
            raise RuntimeError(f"Failed during study guide generation: {str(e)}") from e

    raise RuntimeError(f"Failed during study guide generation after {GEMINI_MAX_ATTEMPTS} attempts: {str(last_error)}") from last_error


def generate_solved_answers(study_text: str, parsed_questions: List[dict]) -> dict:
    """
    Sends study materials and parsed questions to Gemini to solve them,
    returning a structured AnswerPack JSON.
    
    Args:
        study_text: The extracted clean text of the study notes.
        parsed_questions: A list of dicts, each with question_number, question_text, and likely_marks.
        
    Returns:
        A dictionary matching the AnswerPack schema format.
    """
    if not settings.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not configured in settings.")
        raise ValueError("Gemini API key is missing. Please configure GEMINI_API_KEY in your .env file.")
        
    logger.info("Sending parsed questions and study notes to Gemini for solving...")
    
    # Format the parsed questions as a clean bulleted list for the AI
    questions_list_str = ""
    for idx, pq in enumerate(parsed_questions):
        q_num = pq.get("question_number", f"Question {idx+1}")
        q_text = pq.get("question_text", "")
        q_marks = pq.get("likely_marks") or "Unknown"
        questions_list_str += f"- {q_num} | Inferred Marks: {q_marks} | Text: {q_text}\n"

    prompt = f"""
You are an expert AI Solved Answer Pack Compiler.
Your goal is to solve a specific list of parsed exam questions by referring to the provided study notes.

=== STUDY MATERIALS ===
{study_text}

=== SPECIFIC TARGET QUESTIONS TO SOLVE ===
{questions_list_str}

CRITICAL SOLVING & DOMAIN KNOWLEDGE EXTENSION RULES:
1. Priority 1 (Source Truth): Your primary source of truth is the "=== STUDY MATERIALS ===" text. Use it for all concepts, equations, names, and rules.
2. Priority 2 (Partial Coverage): If the study materials cover the topic only partially, extend the answer with concise, standard academic domain knowledge to produce a high-scoring, complete exam answer.
3. Priority 3 (No Coverage / Missing Notes): If the study materials do not cover the topic/question at all, do NOT output a useless dead-end answer (like "not found in notes"). Instead, generate a highly useful exam-ready answer using standard academic domain knowledge. When extending answers this way, you MUST append this exact notice to the end of the answer string:
   "*(Note: Extended beyond uploaded notes.)*"
4. Keep Unicode math symbols, subscripts, superscripts, and Greek letters (e.g. λ, theta, eigenvalues/eigenvectors symbols) intact to preserve formula rendering quality.
5. Apply Marks-Aware Answering:
   Look at the inferred marks/marks category. If not explicitly specified, infer a reasonable category ("2 Marks", "5 Marks", or "10 Marks").
   - **2 Marks** (Short Answers): Provide a concise definition, direct formula, or a 1-2 sentence core explanation.
   - **5 Marks** (Medium Answers): Provide a medium-depth structured explanation, using key bullet points or a short procedural description (around 1 paragraph + 3-5 key points).
   - **10 Marks** (Long Answers / Essays): Provide a detailed and comprehensive response with structured headings, step-by-step logic, full math formulas, derivations, or system architectures.
6. Map the output fields:
   - `question_number`: The label of the question (exactly as provided in the target questions list).
   - `question_text`: The full exact text of the question.
   - `marks_category`: The final marks category: "2 Marks", "5 Marks", or "10 Marks".
   - `answer`: The marks-aware comprehensive exam solution.
   - `simple_explanation`: An intuitive explanation or plain-English analogy explaining the concept/formulas.
   - `quick_revision`: A list of short summary bullet points (3-5 items) for quick review.
   - `memory_trick`: A memory aid (acronym, mnemonic, etc.) to help remember this concept.
   - `related_assets`: Look for any image placeholders (e.g. {{{{IMAGE_ASSET:filename.png}}}}) in the study materials that are directly relevant to this question. Put the exact filenames here.

Return a structured JSON output conforming to the AnswerPack schema containing the list of SolvedQuestion.
"""

    last_error = None
    for attempt in range(1, GEMINI_MAX_ATTEMPTS + 1):
        try:
            logger.info(f"Gemini solving attempt {attempt}/{GEMINI_MAX_ATTEMPTS}...")
            client = genai.Client(api_key=settings.GEMINI_API_KEY)

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=AnswerPack,
                    temperature=0.2
                )
            )

            raw_response_text = response.text
            if not raw_response_text:
                raise ValueError("Received an empty response from Gemini API solver.")

            # Parse and validate response structure using Pydantic model
            answer_pack = AnswerPack.model_validate_json(raw_response_text)
            
            logger.info(
                f"Successfully compiled solved answer pack: '{answer_pack.title}' "
                f"with {len(answer_pack.questions)} solved questions."
            )
            return answer_pack.model_dump()

        except Exception as e:
            last_error = e
            if _is_transient_gemini_error(e) and attempt < GEMINI_MAX_ATTEMPTS:
                delay_seconds = GEMINI_RETRY_DELAYS_SECONDS[attempt - 1]
                logger.warning(
                    f"Gemini attempt {attempt}/{GEMINI_MAX_ATTEMPTS} failed with a transient error: {str(e)}. "
                    f"Retrying in {delay_seconds} seconds..."
                )
                time.sleep(delay_seconds)
                continue

            logger.error(f"Failed during Gemini solving and formatting step: {str(e)}")
            raise RuntimeError(f"Failed during Gemini solving and formatting: {str(e)}") from e

    raise RuntimeError(f"Gemini AI processing failed after {GEMINI_MAX_ATTEMPTS} attempts: {str(last_error)}") from last_error
