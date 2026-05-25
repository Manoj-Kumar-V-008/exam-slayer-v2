import json
import time
from typing import List
from pydantic import ValidationError
from google import genai
from google.genai import types
from app.config import settings
from app.models.schemas import AnswerPack, StudyPack
from app.utils.logger import logger

GEMINI_MAX_ATTEMPTS = 3
GEMINI_RETRY_DELAYS_SECONDS = [10, 30]


def _is_transient_gemini_error(exc: Exception) -> bool:
    """Best-effort detection for retryable Gemini/API failures and socket/network transient drops."""
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
        "getaddrinfo",
        "connection",
        "socket",
        "dns",
        "network",
        "unreachable",
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

            try:
                study_pack = StudyPack.model_validate_json(raw_response_text)
                logger.info(f"Successfully compiled study guide pack: '{study_pack.title}' with {len(study_pack.sections)} sections.")
                return study_pack.model_dump()
            except Exception as val_err:
                logger.error(
                    f"Pydantic validation failed for StudyPack! "
                    f"Response length: {len(raw_response_text)}. "
                    f"Start of response: {raw_response_text[:1000]}... "
                    f"End of response: ...{raw_response_text[-1000:] if len(raw_response_text) > 1000 else raw_response_text}"
                )
                raise val_err

        except Exception as e:
            last_error = e
            is_retryable = (
                _is_transient_gemini_error(e) or
                isinstance(e, ValidationError) or
                isinstance(e, ValueError) or
                "validation" in str(e).lower() or
                "json" in str(e).lower()
            )
            if is_retryable and attempt < GEMINI_MAX_ATTEMPTS:
                delay_seconds = GEMINI_RETRY_DELAYS_SECONDS[attempt - 1]
                logger.warning(f"Retryable error during study guide generation (attempt {attempt}): {str(e)}. Retrying in {delay_seconds}s...")
                time.sleep(delay_seconds)
                continue

            logger.error(f"Failed during study guide generation step: {str(e)}")
            raise RuntimeError(f"Failed during study guide generation: {str(e)}") from e

    raise RuntimeError(f"Failed during study guide generation after {GEMINI_MAX_ATTEMPTS} attempts: {str(last_error)}") from last_error


def generate_solved_answers(study_text: str, parsed_questions: List[dict]) -> dict:
    """
    Sends study materials and parsed questions to Gemini in small batches to solve them,
    returning a aggregated, structured AnswerPack JSON.
    """
    if not settings.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not configured in settings.")
        raise ValueError("Gemini API key is missing. Please configure GEMINI_API_KEY in your .env file.")
        
    if not parsed_questions:
        logger.warning("Empty parsed questions list provided to solver.")
        return {"title": "Solved Answer Pack", "questions": []}
        
    logger.info(f"Solving {len(parsed_questions)} questions in batches to control output size...")
    
    # We batch questions to prevent huge/runaway output and JSON validation issues
    BATCH_SIZE = 2
    batches = [parsed_questions[i:i + BATCH_SIZE] for i in range(0, len(parsed_questions), BATCH_SIZE)]
    
    all_solved_questions = []
    final_title = "Solved Answer Pack"
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    for batch_idx, batch in enumerate(batches):
        logger.info(f"Processing question batch {batch_idx + 1}/{len(batches)} (size: {len(batch)})...")
        
        # Format the parsed questions in this batch as a clean bulleted list for the AI
        questions_list_str = ""
        for idx, pq in enumerate(batch):
            q_num = pq.get("question_number", f"Question {batch_idx * BATCH_SIZE + idx + 1}")
            q_text = pq.get("question_text", "")
            q_marks = pq.get("likely_marks") or "Unknown"
            questions_list_str += f"- {q_num} | Inferred Marks: {q_marks} | Text: {q_text}\n"

        prompt = f"""
You are a highly concise, expert AI Solved Answer Pack Compiler.
Your goal is to solve a specific list of parsed exam questions by referring to the provided study notes.

=== STUDY MATERIALS ===
{study_text}

=== TARGET QUESTIONS TO SOLVE IN THIS BATCH ===
{questions_list_str}

CRITICAL RULES FOR BREVITY & VERBOSITY CONTROL:
1. STRICT WORD LIMITS PER QUESTION:
   For the 'answer' field of each question:
   - If the marks category is "2 Marks", the answer MUST be between 80 and 150 words. Do NOT write more than 150 words.
   - If the marks category is "5 Marks", the answer MUST be between 200 and 350 words. Do NOT write more than 350 words.
   - If the marks category is "10 Marks", the answer MUST be between 400 and 700 words. Do NOT write more than 700 words.
2. NO VERBOSITY BLOAT:
   - Do NOT generate textbook explanations, historical background, or generic introductions.
   - Do NOT repeat concepts. Write dense, high-scoring exam points and stop immediately.
   - Do NOT expand answers endlessly. Keep every sentence functional and direct.
3. SCHEMA FIELD BREVITY (CONCISE OUTPUT):
   Conform to the AnswerPack schema and provide these fields for each question:
   - `question_number`: Exactly as given in target list.
   - `question_text`: Exactly as given in target list.
   - `marks_category`: "2 Marks", "5 Marks", or "10 Marks".
   - `answer`: The exam-ready solution conforming strictly to the word limits above.
   - `simple_explanation`: A very brief (max 60 words), intuitive plain-English analogy or summary.
   - `quick_revision_points`: Exactly 3-5 short bullet points (max 10 words per bullet).
   - `memory_trick`: A short (max 15 words) memory aid or mnemonic.
   - `related_assets`: Filename pointers to relevant images in the study materials if any.

CRITICAL SOLVING & DOMAIN KNOWLEDGE EXTENSION RULES:
- Priority 1 (Source Truth): Use the "=== STUDY MATERIALS ===" as the primary source of truth.
- Priority 2 (Partial Coverage): If the study materials cover the topic only partially, extend the answer with concise, standard academic domain knowledge to produce a complete exam answer.
- Priority 3 (No Coverage / Missing Notes): If not covered at all, generate a highly useful exam-ready answer using standard academic domain knowledge, and append this exact notice to the end of the answer string:
  "*(Note: Extended beyond uploaded notes.)*"
- Keep Unicode math symbols, subscripts, superscripts, and Greek letters (e.g. λ, θ) intact to preserve formula rendering quality.

Return a structured JSON output conforming to the AnswerPack schema containing the list of SolvedQuestion.
"""

        batch_error = None
        for attempt in range(1, GEMINI_MAX_ATTEMPTS + 1):
            try:
                logger.info(f"Gemini solving attempt {attempt}/{GEMINI_MAX_ATTEMPTS} for batch {batch_idx + 1}...")
                
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

                try:
                    # Parse and validate response structure using Pydantic model
                    answer_pack = AnswerPack.model_validate_json(raw_response_text)
                    
                    logger.info(
                        f"Successfully compiled solved answer pack batch {batch_idx + 1}: "
                        f"'{answer_pack.title}' with {len(answer_pack.questions)} solved questions."
                    )
                    
                    if batch_idx == 0:
                        final_title = answer_pack.title
                        
                    for q in answer_pack.questions:
                        all_solved_questions.append(q.model_dump())
                        
                    break  # Success, break attempt loop for this batch
                    
                except Exception as val_err:
                    logger.error(
                        f"Pydantic validation failed for AnswerPack batch {batch_idx + 1}! "
                        f"Response length: {len(raw_response_text)}. "
                        f"Start of response: {raw_response_text[:1000]}... "
                        f"End of response: ...{raw_response_text[-1000:] if len(raw_response_text) > 1000 else raw_response_text}"
                    )
                    raise val_err

            except Exception as e:
                batch_error = e
                is_retryable = (
                    _is_transient_gemini_error(e) or
                    isinstance(e, ValidationError) or
                    isinstance(e, ValueError) or
                    "validation" in str(e).lower() or
                    "json" in str(e).lower()
                )
                if is_retryable and attempt < GEMINI_MAX_ATTEMPTS:
                    delay_seconds = GEMINI_RETRY_DELAYS_SECONDS[attempt - 1]
                    logger.warning(
                        f"Gemini attempt {attempt}/{GEMINI_MAX_ATTEMPTS} for batch {batch_idx + 1} failed: {str(e)}. "
                        f"Retrying in {delay_seconds} seconds..."
                    )
                    time.sleep(delay_seconds)
                    continue

                logger.error(f"Failed during Gemini solving for batch {batch_idx + 1}: {str(e)}")
                raise RuntimeError(f"Failed during Gemini solving for batch {batch_idx + 1}: {str(e)}") from e
        else:
            raise RuntimeError(f"Failed to solve batch {batch_idx + 1} after {GEMINI_MAX_ATTEMPTS} attempts.") from batch_error

    # Return the aggregated AnswerPack
    final_pack = {
        "title": final_title,
        "questions": all_solved_questions
    }
    logger.info(f"Fully compiled answer pack with a total of {len(all_solved_questions)} solved questions.")
    return final_pack
