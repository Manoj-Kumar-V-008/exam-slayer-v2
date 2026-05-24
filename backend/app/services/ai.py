import json
import time
from google import genai
from google.genai import types
from app.config import settings
from app.models.schemas import StudyPack
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
    Sends raw extracted text to Gemini to clean up, simplify, and structure
    into a student-friendly study pack JSON output while preserving asset placeholders.
    
    Args:
        raw_text: The layout-sorted extracted text with inline image placeholders.
        
    Returns:
        A dictionary matching the StudyPack schema format.
    """
    if not settings.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not configured in environment settings.")
        raise ValueError("Gemini API key is missing. Please configure GEMINI_API_KEY in your .env file.")
        
    logger.info("Sending content to Gemini for study pack generation...")
    
    prompt = f"""
You are an expert academic tutor, examiner, and content compiler. 
Your task is to convert raw extracted academic materials into a premium, clean, exam-ready study guide.

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
    - You are allowed and encouraged to use standard semantic markdown syntax in string fields to enhance readability and structure:
      - Use **bold** to highlight key terms, rules, and definitions.
      - Use *italics* for minor emphasis or citations.
      - Use inline code backticks `like_this` for programming keywords, variables, or tech terms.
      - Use inline headers (like ### Sub-topic) inside the simple_explanation or summary if needed to group details.
      - Use Unicode math symbols for formulas and equations.
    - Do NOT use raw HTML.
    - Do NOT use markdown code blocks/fences (e.g. ```python) unless explicitly demonstrating a programming snippet.
    - Ensure all markdown elements are well-formed and clean.
12. CRITICAL ASSET RULES:
    - You must preserve all image/diagram asset placeholders from the raw text EXACTLY as they appear.
    - Placeholders are in the format: {{{{IMAGE_ASSET:filename.png}}}}
    - If you encounter a placeholder, decide exactly which section it belongs to based on the surrounding context.
    - Extract the exact filename (e.g. 'abc123_img_1.png') and place it inside the 'embedded_assets' list for that section.
    - DO NOT rename, omit, or invent placeholders. Under no circumstances should you hallucinate filenames.
    - Only filenames found inside a {{{{IMAGE_ASSET:filename}}}} pattern in the raw text can be included in 'embedded_assets'.
    - If no placeholders belong to a section, leave 'embedded_assets' as an empty list [].

RAW MATERIAL TO PROCESS:
{raw_text}
"""

    last_error = None

    for attempt in range(1, GEMINI_MAX_ATTEMPTS + 1):
        try:
            logger.info(f"Gemini study pack generation attempt {attempt}/{GEMINI_MAX_ATTEMPTS}...")

            # Initialize Google GenAI client
            client = genai.Client(api_key=settings.GEMINI_API_KEY)

            # Call Gemini model requesting structured JSON output conforming to StudyPack
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

            # Parse and validate response structure using Pydantic model
            study_pack = StudyPack.model_validate_json(raw_response_text)

            logger.info(
                f"Successfully compiled study guide pack: '{study_pack.title}' "
                f"with {len(study_pack.sections)} sections."
            )
            return study_pack.model_dump()

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

            if _is_transient_gemini_error(e):
                error_message = (
                    f"Gemini AI processing failed after {GEMINI_MAX_ATTEMPTS} attempts "
                    f"due to rate limit/quota or transient API errors: {str(e)}"
                )
            else:
                error_message = f"Failed during Gemini cleanup and formatting step: {str(e)}"

            logger.error(error_message)
            raise RuntimeError(error_message) from e

    error_message = (
        f"Gemini AI processing failed after {GEMINI_MAX_ATTEMPTS} attempts: {str(last_error)}"
    )
    logger.error(error_message)
    raise RuntimeError(error_message) from last_error
