import json
import time
from pathlib import Path
from typing import List, Optional, Any, Union
from pydantic import ValidationError
from google import genai
from google.genai import types
from app.config import settings
from app.models.schemas import AnswerPack, StudyPack
from app.utils.logger import logger
from app.utils.text_cleaner import compress_study_context_for_batch
from app.services.gemini_router import generate_content_with_routing


VISION_INSTRUCTIONS = """
VISION GROUNDING (attached page renders):
- {n} rendered PDF page image(s) are attached alongside the extracted text.
- Use them as source truth for diagrams, tables, formulas, and layout.
- Transcribe tables/formulas exactly; describe each diagram's components and relationships.
- When a section explains a diagram, reference its visual structure explicitly.
"""

VisionImages = Optional[List[Union[str, Path, bytes]]]


def clean_study_notes(raw_text: str, vision_images: VisionImages = None) -> dict:
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
    vision_block = VISION_INSTRUCTIONS.format(n=len(vision_images)) if vision_images else ""
    logger.info(f"Study pack vision images: {len(vision_images) if vision_images else 0}")
    
    prompt = f"""
You are an expert academic tutor, examiner, and content compiler. 
Your task is to convert raw extracted academic materials into a premium, clean, exam-ready study guide.
{vision_block}
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
            temperature=0.2,
            vision_images=vision_images,
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
    models: List[str],
    vision_images: VisionImages = None,
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
        q_dominant = pq.get("dominant_intent") or "theory"
        q_sub_intents = pq.get("sub_intents") or []
        
        q_matched_imgs = pq.get("matched_images", [])
        if q_matched_imgs:
            imgs_info = "; ".join([f"{img['filename']} (Caption: '{img['caption']}')" for img in q_matched_imgs])
        else:
            imgs_info = "None"
            
        questions_list_str += (
            f"- {q_num} | Inferred Marks: {q_marks} | Dominant Intent: {q_dominant} "
            f"| Sub-Intents: {q_sub_intents} | Matched Diagrams to Discuss: {imgs_info} | Text: {q_text}\n"
        )

    prompt = f"""
You are an expert AI Solved Answer Pack Compiler.
Your goal is to solve a specific list of parsed exam questions by referring to the provided study notes.
The target output is a set of premium, university-exam model answers designed to maximize scoring.
{VISION_INSTRUCTIONS.format(n=len(vision_images)) if vision_images else ""}
=== STUDY MATERIALS ===
{compressed_context}

=== TARGET QUESTIONS TO SOLVE IN THIS BATCH ===
{questions_list_str}

=== CRITICAL PRINCIPLES FOR DYNAMIC, SUBJECT-AGNOSTIC ANSWER COMPOSITION ===
Exam Slayer is a subject-agnostic academic system. It must work equally well for DBMS, Operating Systems, Computer Networks, Algorithms, Data Structures, AI/ML, Mathematics, Programming, Theory subjects, and future engineering subjects. The system must adapt to the question.

1. THE EXCELLENT TEACHER RULE (SIMPLE & SMOOTH ENGLISH):
   - Rewrite explanations into simple, smooth, natural, and conversational English.
   - Strictly avoid complex sentences, textbook-style wording, or dry academic jargon.
   - Keep sentences short. Focus on absolute clarity over sophisticated vocabulary.
   - If a concept can be explained in a simpler way without losing meaning, do it. Write as if you are a friendly, excellent tutor helping a student memorize concepts easily.

2. STRUCTURED BULLET POINTS:
   - Structure answers using clean, bullet-pointed lists (e.g. • Key Point 1) wherever appropriate instead of walls of text. Avoid paragraphs longer than 3 lines.

3. TOOLBOX PRINCIPLE & INTELLIGENT COMPONENT SELECTION:
   - Answer components are a toolbox, NOT a checklist. Select only the components that genuinely improve the answer. Do NOT automatically include Architecture, Applications, Advantages, Disadvantages, Comparisons, Examples, or Limitations unless they naturally fit the question.
   - Intelligently select from these available components to build a natural, topic-aware flow under clear subsection headings (e.g., `### Component Name`):
     - Definition / Concept Overview
     - Core Explanation / Working Principle
     - Architecture / Components (Render as compact, scannable markdown tables)
     - Formula / Mathematical Derivation / Theorem
     - Algorithm / Pseudocode / Process / Step-by-Step Procedure (Render as ordered numbered lists)
     - Example / Code Block / SQL Query / Relational Algebra Expression
     - Schema Design / ER Mapping (Use formal mappings with underlined primary keys)
     - Diagram Explanation (Detailed textual description; do NOT generate ASCII art)
     - Comparison Table (Render always as a clean markdown table comparing metrics/features side-by-side)
     - Advantages / Disadvantages / Limitations (Bulleted lists)
     - Applications / Use Cases

4. INTENT-DRIVEN PRIORITIZATION:
   - The `dominant_intent` determines the answer emphasis, largest content allocation, and answer organization.
   - **CRITICAL CODE/SQL RULE**: If SQL, code, or programming logic is the dominant intent, start the 'answer' field IMMEDIATELY with the code/query block. Do NOT write any introduction or conversational context before it.

5. STRICT MARKS-AWARE WORD LIMITS:
   - You MUST satisfy these word counts for every single question.
   - **2 Marks**: Target 80–150 words. Direct answer. Concise but complete.
   - **5 Marks**: Target 200–350 words. Structured explanation with examples/tables.
   - **10 Marks**: Target 500–800 words. Comprehensive university-level answer. Generate as many sections as necessary to comprehensively answer the question (typical range is 4–8 sections).
   - Every 10 Marks answer MUST be at least 450-800 words (aim for 550+ words). Prioritize completeness and depth to naturally reach this length.

6. FORMATTING & READABILITY RULES (5-SECOND SCANNING RULE):
   - Students should understand the answer structure within 5 seconds. Use whitespace, clear section separation, and heading hierarchy.
   - **Keyword Highlighting**: Bold important concepts and technical terms (e.g., `**Time Complexity**`, `**Virtual Memory**`) so students can instantly identify them while scrolling.
   - **Tables**: Use markdown tables (`| Column 1 | Column 2 |`) for comparisons and architectures.

7. GROUNDING & DOMAIN KNOWLEDGE EXTENSION:
   - Priority 1 (Source Truth): Use the "=== STUDY MATERIALS ===" as the primary source of truth.
   - Priority 2 (No Coverage): If the study notes are insufficient, fall back to your general model knowledge silently and seamlessly. Do NOT append any disclaimers like "*(Note: Extended beyond uploaded notes.)*".

8. STRICT NO-IMAGE-PLACEHOLDERS RULE:
   - Do NOT write or output any image placeholders like `{{IMAGE_ASSET:...}}` or HTML image tags in the 'answer' text. The system handles all diagram placement programmatically after you generate the text.

9. SCHEMA FIELD STRUCTURE:
   Conform to the AnswerPack schema and provide these fields for each question:
   - `question_number`: Exactly as given in target list.
   - `question_text`: Exactly as given in target list.
   - `marks_category`: "2 Marks", "5 Marks", or "10 Marks" (inferred or explicit).
   - `dominant_intent`: Exactly as given in target list.
   - `sub_intents`: Exactly as given in target list.
   - `answer`: The exam-ready solution conforming strictly to the word limits, formatting, and simple English instructions.
   - `simple_explanation`: A very brief (max 50 words) intuitive plain-English analogy.
   - `quick_revision_points`: Exactly 3 short bullet points (max 8 words per bullet) summarizing key takeaways.
   - `memory_trick`: A short, high-value "Quick Remember" summary or mnemonic (max 12 words), prefixed with "Quick Remember: " (e.g. `Quick Remember: DBMS ensures data integrity`).
   - `related_assets`: Keep this list empty. The system will populate it programmatically.

Keep Unicode math symbols, subscripts, superscripts, and Greek letters (e.g. λ, θ) intact to preserve formula rendering quality.

Return a structured JSON output conforming to the AnswerPack schema containing the list of SolvedQuestion.
"""
    answer_pack = generate_content_with_routing(
        prompt=prompt,
        response_schema=AnswerPack,
        models=models,
        pipeline_name="ANSWER_PACK",
        temperature=0.2,
        vision_images=vision_images,
    )
    return [q.model_dump() for q in answer_pack.questions]


def generate_solved_answers(
    study_text: str,
    parsed_questions: List[dict],
    vision_images: VisionImages = None,
) -> dict:
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
                models=settings.ANSWER_PACK_MODELS,
                vision_images=vision_images,
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
                
    # Post-process: Map matched images back and programmatically place placeholders in answers
    from app.services.image_intelligence import place_images_in_answer
    matched_images_map = {q.get("question_number"): q.get("matched_images", []) for q in parsed_questions}
    
    for sq in all_solved_questions:
        q_num = sq.get("question_number")
        matched_imgs = matched_images_map.get(q_num, [])
        sq["matched_images"] = matched_imgs
        # Sync assets lists
        sq["related_assets"] = [img["filename"] for img in matched_imgs]
        sq["embedded_assets"] = [img["filename"] for img in matched_imgs]
        
        # Inject the placeholders programmatically under the most relevant headings
        sq["answer"] = place_images_in_answer(sq.get("answer", ""), matched_imgs)
        
    return {
        "title": final_title,
        "questions": all_solved_questions
    }

def generate_things_to_remember(study_text: str, solved_questions: List[dict]) -> List[dict]:
    """
    Generates a topic-wise list of key points, classification types, and terms to remember
    by analyzing the generated questions/answers and study notes.
    """
    if not settings.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not configured. Skipping revision sheets generation.")
        return []

    logger.info("Generating 'Things to Remember' (Quick Revision sheets)...")
    
    # Create summary list of questions and answers to feed into prompt
    qa_summary = ""
    for sq in solved_questions:
        qa_summary += f"Question {sq.get('question_number')}: {sq.get('question_text')}\nAnswer Brief: {sq.get('simple_explanation')}\nKey Points: {', '.join(sq.get('quick_revision_points', []))}\n\n"

    # We want a list of TopicRevisionSummary
    from app.models.schemas import TopicRevisionSummary
    from pydantic import BaseModel
    
    class RevisionList(BaseModel):
        topics: List[TopicRevisionSummary]

    prompt = f"""
    You are an expert academic tutor compiling a master revision cheatsheet called "Things to Remember".
    Based on the following solved exam questions/answers and study notes, create a clean topic-wise summary.
    
    Focus on:
    - Essential classification types (e.g. types of DBMS architectures, types of normal forms, types of transactions, etc.).
    - Core keywords and definitions that students must write in exams.
    - Essential formulas, rules, or key steps to memorize.
    
    Style instructions:
    - Group items logically by topic/chapter (aim for 3-5 distinct topics).
    - Under each topic, provide exactly 4-6 concise, bullet-pointed sentences of key facts or types to memorize.
    - Use simple, direct, smooth English. Avoid textbook jargon.
    
    === SOLVED QUESTIONS & ANSWERS SUMMARY ===
    {qa_summary}
    
    === STUDY NOTES Passages ===
    {study_text[:20000]}
    
    Return a structured JSON output matching the RevisionList schema.
    """
    
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    models = settings.QUESTION_PARSER_MODELS
    
    for model in models:
        try:
            logger.info(f"Generating Revision Sheets using model: {model}")
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=RevisionList,
                    temperature=0.2
                )
            )
            if response.text:
                parsed = RevisionList.model_validate_json(response.text)
                return [t.model_dump() for t in parsed.topics]
        except Exception as e:
            logger.warning(f"Failed to generate revision sheets using model {model}: {e}")
            continue
            
    return []

