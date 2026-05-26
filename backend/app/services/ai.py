import json
import time
from typing import List, Optional, Any
from pydantic import ValidationError
from google import genai
from google.genai import types
from app.config import settings
from app.models.schemas import AnswerPack, StudyPack
from app.utils.logger import logger
from app.utils.text_cleaner import compress_study_context_for_batch
from app.services.gemini_router import generate_content_with_routing


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
        
    logger.info("Preparing content for study pack guide generation...")
    
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
    try:
        study_pack = generate_content_with_routing(
            prompt=prompt,
            response_schema=StudyPack,
            models=settings.STUDY_PACK_MODELS,
            pipeline_name="STUDY_PACK",
            temperature=0.2
        )
        return study_pack.model_dump()
    except Exception as e:
        logger.error(f"Failed during study guide generation step: {str(e)}")
        raise RuntimeError(f"Failed during study guide generation: {str(e)}") from e


def _solve_question_batch(
    study_text: str,
    batch_questions: List[dict],
    batch_idx: int,
    total_batches: int,
    models: List[str]
) -> List[dict]:
    """
    Solves a single batch of questions. Automatically handles context compression for the batch.
    If the batch fails, it throws an error so the caller can split the batch dynamically.
    """
    # 1. Compress context for this specific batch of questions
    compressed_context = compress_study_context_for_batch(
        study_text=study_text,
        batch_questions=batch_questions,
        max_chars=settings.MAX_ANSWER_PACK_CONTEXT_CHARS
    )
    
    # 2. Format question list
    questions_list_str = ""
    for idx, pq in enumerate(batch_questions):
        q_num = pq.get("question_number", f"Question {idx + 1}")
        q_text = pq.get("question_text", "")
        q_marks = pq.get("likely_marks") or "Unknown"
        questions_list_str += f"- {q_num} | Inferred Marks: {q_marks} | Text: {q_text}\n"

    prompt = f"""
You are a highly concise, expert AI Solved Answer Pack Compiler.
Your goal is to solve a specific list of parsed exam questions by referring to the provided study notes.
The target student wants to finish reading this pack quickly and feel confident. Every word must count.

=== STUDY MATERIALS ===
{compressed_context}

=== TARGET QUESTIONS TO SOLVE IN THIS BATCH ===
{questions_list_str}

CRITICAL RULES FOR BREVITY, EXAM FOCUS & VALUE DENSITY (COMPENSATE FOR LIGHTER MODELS):
1. STRICT WORD LIMITS PER QUESTION (For the 'answer' field):
   - If the marks category is "2 Marks", the answer MUST be extremely direct, concise and short: 30 to 70 words. State the definition or direct answer instantly. Do NOT add unnecessary background or introductory fluff.
   - If the marks category is "5 Marks", the answer MUST be between 100 and 180 words. Keep it compact, high-value, and direct. Use bullets for core elements and a short explanation.
   - If the marks category is "10 Marks", the answer MUST be between 200 and 380 words. Provide key concepts, structured comparison, or procedure details using concise bullet formatting. Detailed but revision-friendly; strictly avoid textbook essays or historical background.
2. NO VERBOSITY OR ACADEMIC FLUFF:
   - Do NOT write introductory filler like "In this section we will look at..." or "As described in the study notes...".
   - Start immediately with the direct answer.
   - Never repeat definitions or concepts within the same answer.
   - Use examples ONLY if they are brief and genuinely help clarify the concept.
3. STRUCTURED CONTENT RENDERING (CRITICAL):
   - **SQL & Code Snippets:** Wrap all programming code, database schemas, and SQL queries in proper markdown code blocks (e.g., use ```sql ... ``` or ```c ... ```).
   - **Tabular Comparisons & Structured Data:** If a question asks for comparisons (e.g., "DBMS vs File Systems" or "Logical vs Physical independence") or lists differences, advantages/disadvantages, you MUST render them inside a clean **markdown table** (e.g. `| Column 1 | Column 2 |` with `|---|---|` dividers). Do NOT use plain ASCII layouts.
4. TOPPER-GRADE ACADEMIC QUALITY:
   - Provide topper-grade academic answers. Use precise technical terminology.
   - Bold critical terms when they are first defined.
   - Make the `memory_trick` highly relevant, such as creative acronyms or mnemonics (e.g. "ACID = Atomicity, Consistency, Isolation, Durability").
5. SCHEMA FIELD BREVITY (CONCISE OUTPUT):
   Conform to the AnswerPack schema and provide these fields for each question:
   - `question_number`: Exactly as given in target list.
   - `question_text`: Exactly as given in target list.
   - `marks_category`: "2 Marks", "5 Marks", or "10 Marks".
   - `answer`: The exam-ready solution conforming strictly to the word limits and markdown rules above. Use bullet points or bold keys where appropriate.
   - `simple_explanation`: A very brief (max 50 words) intuitive plain-English analogy or high-level summary.
   - `quick_revision_points`: Exactly 3 short bullet points (max 8 words per bullet) summarizing the key takeaway.
   - `memory_trick`: A short (max 12 words) mnemonic or quick association trigger.
   - `related_assets`: Filename pointers to relevant images in the study materials if any.

CRITICAL SOLVING & DOMAIN KNOWLEDGE EXTENSION RULES:
- Priority 1 (Source Truth): Use the "=== STUDY MATERIALS ===" as the primary source of truth.
- Priority 2 (Partial Coverage): If the study materials cover the topic only partially, extend the answer with concise, standard academic domain knowledge to produce a complete exam answer.
- Priority 3 (No Coverage / Missing Notes): If not covered at all, generate a highly useful exam-ready answer using standard academic domain knowledge, and append this exact notice to the end of the answer string:
  "*(Note: Extended beyond uploaded notes.)*"
- Keep Unicode math symbols, subscripts, superscripts, and Greek letters (e.g. λ, θ) intact to preserve formula rendering quality.

Return a structured JSON output conforming to the AnswerPack schema containing the list of SolvedQuestion.
"""
    answer_pack = generate_content_with_routing(
        prompt=prompt,
        response_schema=AnswerPack,
        models=models,
        pipeline_name="ANSWER_PACK",
        temperature=0.2
    )
    return [q.model_dump() for q in answer_pack.questions]


def generate_solved_answers(study_text: str, parsed_questions: List[dict]) -> dict:
    """
    Sends study materials and parsed questions to Gemini in batches to solve them.
    Features dynamic batch size reduction if solving fails due to schema validation or other errors.
    """
    if not settings.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not configured in settings.")
        raise ValueError("Gemini API key is missing. Please configure GEMINI_API_KEY in your .env file.")
        
    if not parsed_questions:
        logger.warning("Empty parsed questions list provided to solver.")
        return {"title": "Solved Answer Pack", "questions": []}
        
    logger.info(f"Solving {len(parsed_questions)} questions with dynamic batching and fallback protection...")
    
    # We initialize the queue of batches.
    batch_size = settings.ANSWER_PACK_BATCH_SIZE
    batches_queue = [parsed_questions[i:i + batch_size] for i in range(0, len(parsed_questions), batch_size)]
    
    all_solved_questions = []
    final_title = "Solved Answer Pack"
    
    batch_counter = 0
    while batches_queue:
        current_batch = batches_queue.pop(0)
        batch_counter += 1
        total_batches_remaining = len(batches_queue) + 1
        
        logger.info(f"Processing question batch (size: {len(current_batch)}, remaining queue size: {len(batches_queue)})...")
        
        try:
            solved_questions = _solve_question_batch(
                study_text=study_text,
                batch_questions=current_batch,
                batch_idx=batch_counter,
                total_batches=total_batches_remaining,
                models=settings.ANSWER_PACK_MODELS
            )
            all_solved_questions.extend(solved_questions)
            
            if batches_queue:
                logger.info("Sleeping 5 seconds between batches...")
                time.sleep(5)
                
        except Exception as e:
            logger.warning(f"Batch solving failed for batch of size {len(current_batch)}: {str(e)}")
            
            if len(current_batch) > 1:
                mid = len(current_batch) // 2
                batch_1 = current_batch[:mid]
                batch_2 = current_batch[mid:]
                logger.warning(
                    f"Dynamically reducing batch size! Splitting batch of size {len(current_batch)} "
                    f"into two sub-batches of size {len(batch_1)} and {len(batch_2)}."
                )
                batches_queue.insert(0, batch_2)
                batches_queue.insert(0, batch_1)
                batch_counter -= 1
            else:
                logger.error(f"Single-question batch failed permanently. Cannot split further: {str(e)}")
                raise e
                
    return {
        "title": final_title,
        "questions": all_solved_questions
    }
