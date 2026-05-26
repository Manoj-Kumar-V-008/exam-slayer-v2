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
        q_type = pq.get("question_type") or "theory"
        questions_list_str += f"- {q_num} | Inferred Marks: {q_marks} | Type: {q_type} | Text: {q_text}\n"

    prompt = f"""
You are an expert AI Solved Answer Pack Compiler.
Your goal is to solve a specific list of parsed exam questions by referring to the provided study notes.
The target output is a set of premium, university-exam model answers designed to maximize scoring.

=== STUDY MATERIALS ===
{compressed_context}

=== TARGET QUESTIONS TO SOLVE IN THIS BATCH ===
{questions_list_str}

CRITICAL RULES FOR MARKS-AWARE ANSWER DEPTH & QUESTION TYPE FORMATTING:
1. STRICT WORD LIMITS PER QUESTION (For the 'answer' field):
   - You MUST satisfy these word counts for every single question. Writing too short answers is a severe failure.
   - 2 Marks: 80–150 words. Direct answer only.
   - 5 Marks: 200–350 words. Structured explanation + brief example.
   - 10 Marks: 450–800 words. Deep, highly detailed, exam-ready response. You must expand the concepts comprehensively, explain all relevant parts, give clear step-by-step processes or schema diagrams, add code/queries if applicable, compare alternatives, and write a thorough, deep, university-level answer. Do not write short summaries or brief outlines.
   - NOTE: Since the provided study notes may be brief summary pointers, you MUST expand the answers using your own deep academic domain knowledge to meet these word limits. If you write less than 450 words for a 10 Marks question or less than 200 words for a 5 Marks question, it will fail validation. You have plenty of output token space because this batch contains limited questions. Use it to write a comprehensive, long, detailed response.
   - If the marks category is "Unknown" or missing in the target list, infer the marks based on complexity (e.g., direct definitions -> 2 marks, comparisons/explanations -> 5 marks, design/complex analysis/SQL schema queries -> 10 marks) and apply the correct word limits.

2. FORMATTING RULES BY QUESTION TYPE (For the 'answer' field):
   - 'theory': Must contain:
     - Introduction: Concise definition/context.
     - Explanation: Multi-layered structured explanation of concepts.
     - Examples: Real-world or academic examples.
     - Comparisons: (If relevant) comparative analysis.
     - Mnemonic: Memory hook/acronym.
     - Quick Revision Summary: Key takeaway bullets.
   - 'sql': Directly output query blocks using markdown (```sql ... ```). Follow with line-by-line mechanical explanation and column meanings. Strictly avoid conversational chatbot-style filler.
   - 'relational_algebra': Output formal algebraic expressions. Provide operator breakdowns.
   - 'er_model': Output relational schema attributes (underlined PK, italic FK), key constraints, mapping steps, and details.
   - 'definition': Concise, clear, high-scoring academic definition.
   - 'comparison': Must render a clean markdown table comparing key metrics. Do not use plain text lists.
   - 'problem_solving': Clear step-by-step mathematical/procedural solution.
   - 'mixed': Combine query blocks and step-by-step structured theory as appropriate.

3. UNIVERSITY-GRADE QUALITY & STYLE:
   - Target a formal, academic, clear, teacher-friendly, university exam scoring-oriented tone.
   - Strictly avoid chatbot-style dialogue, conversational filler (e.g., "Sure, here is the answer", "In this section we will discuss"), and introductory/concluding remarks.
   - Use precise technical terminology. Bold key terms when first defined.
   - Wrap all code, schemas, and queries in proper markdown blocks.

4. GROUNDING & DOMAIN KNOWLEDGE EXTENSION:
   - Priority 1 (Source Truth): Use the "=== STUDY MATERIALS ===" as the primary source of truth.
   - Priority 2 (No Coverage / Missing Notes): If the study notes are insufficient or lack coverage of a question, you must fall back to your general model knowledge silently and seamlessly.
   - **CRITICAL**: Do NOT append any footnotes, notices, or warning disclaimers like "*(Note: Extended beyond uploaded notes.)*" under any circumstances. Proceed silently and seamlessly.

5. SCHEMA FIELD STRUCTURE:
   Conform to the AnswerPack schema and provide these fields for each question:
   - `question_number`: Exactly as given in target list.
   - `question_text`: Exactly as given in target list.
   - `marks_category`: "2 Marks", "5 Marks", or "10 Marks" (inferred or explicit).
   - `question_type`: Exactly as given in target list.
   - `answer`: The exam-ready solution conforming strictly to the word limits, formatting, and markdown rules above.
   - `simple_explanation`: A very brief (max 50 words) intuitive plain-English analogy.
   - `quick_revision_points`: Exactly 3 short bullet points (max 8 words per bullet) summarizing the key takeaways.
   - `memory_trick`: A short (max 12 words) mnemonic or quick association trigger.
   - `related_assets`: Filename pointers to relevant images in the study materials if any.

Keep Unicode math symbols, subscripts, superscripts, and Greek letters (e.g. λ, θ) intact to preserve formula rendering quality.

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
    Isolates 10 Marks questions into their own single-question batches to guarantee maximum length and depth.
    """
    if not settings.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not configured in settings.")
        raise ValueError("Gemini API key is missing. Please configure GEMINI_API_KEY in your .env file.")
        
    if not parsed_questions:
        logger.warning("Empty parsed questions list provided to solver.")
        return {"title": "Solved Answer Pack", "questions": []}
        
    logger.info(f"Solving {len(parsed_questions)} questions with dynamic marks-aware batching...")
    
    # We initialize the queue of batches.
    # Group questions: 10 Marks questions get isolated into batches of size 1.
    # Other questions (2 Marks, 5 Marks) are grouped into batches of up to 3.
    batches_queue = []
    current_small_batch = []
    
    for pq in parsed_questions:
        marks = pq.get("likely_marks", "") or ""
        # If it's a 10 Marks question, isolate it in its own batch
        if "10" in marks:
            if current_small_batch:
                batches_queue.append(current_small_batch)
                current_small_batch = []
            batches_queue.append([pq])
        else:
            current_small_batch.append(pq)
            if len(current_small_batch) >= 3:
                batches_queue.append(current_small_batch)
                current_small_batch = []
                
    if current_small_batch:
        batches_queue.append(current_small_batch)
        
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
