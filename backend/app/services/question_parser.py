import json
import time
import re
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from app.config import settings
from app.utils.logger import logger
from app.services.gemini_router import generate_content_with_routing

class ParsedQuestion(BaseModel):
    question_number: str = Field(..., description="The numbering or label of the question, e.g., 'Question 1', 'Question 2(a)'.")
    question_text: str = Field(..., description="The full wording of the question.")
    likely_marks: Optional[str] = Field(None, description="The estimated or explicit marks category, e.g. '2 Marks', '5 Marks', '10 Marks'.")
    question_type: str = Field(..., description="The classified type of the question: 'theory', 'definition', 'sql', 'relational_algebra', 'er_model', 'comparison', 'problem_solving', 'mixed'.")

class ParsedQuestionList(BaseModel):
    questions: List[ParsedQuestion] = Field(..., description="The list of parsed questions.")

def extract_candidate_blocks(raw_qb_text: str) -> List[dict]:
    """
    Deterministically splits raw question bank text into candidate question blocks
    using regular expressions and sequence-tracking heuristics.
    """
    lines = raw_qb_text.splitlines()
    candidates = []
    current_block_lines = []
    current_q_num = None
    last_num = None
    section_header_seen = False
    
    # Regex to match top-level question prefixes:
    # 1. Question/Q followed by digit(s), optional marks, optional punctuation
    # 2. Standalone digits followed by period/closing parenthesis/dash
    # 3. Digits enclosed in parentheses
    pattern = re.compile(
        r"^\s*(?:"
        r"(?:Question|Q)\s*(\d+)(?:\s*(?:\(\s*\d+\s*(?:marks?|m)\s*\))?\s*[\.:\-)])?"
        r"|(\d+)\s*[\.:\-)]"
        r"|\(\s*(\d+)\s*\)"
        r")",
        re.IGNORECASE
    )
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_block_lines:
                current_block_lines.append(line)
            continue
            
        # Detect section headers to allow numbering reset safely
        if re.search(r"\b(section|part|module|group)\b", stripped, re.IGNORECASE) and len(stripped) < 40:
            section_header_seen = True
            
        match = pattern.match(line)
        if match:
            q_num_str = match.group(1) or match.group(2) or match.group(3)
            q_num = int(q_num_str)
            
            is_new_q = False
            if match.group(1) is not None:
                # Explicit "Question 1" or "Q1" prefix always starts a new question
                is_new_q = True
            elif last_num is None:
                # First question encountered
                is_new_q = True
            elif q_num > last_num:
                # Numbers are strictly increasing
                is_new_q = True
            elif q_num == 1 and (last_num > 1 and section_header_seen):
                # Allowed reset to 1 if we saw a section header recently
                is_new_q = True
                section_header_seen = False
                
            if is_new_q:
                # Save previous candidate block
                if current_block_lines:
                    text_content = "\n".join(current_block_lines).strip()
                    if text_content:
                        candidates.append({
                            "question_number": current_q_num or "Intro/Header",
                            "raw_block": text_content
                        })
                
                # Start new question block
                current_q_num = str(q_num)
                last_num = q_num
                current_block_lines = [line]
                continue
                
        current_block_lines.append(line)
        
    # Save the final block
    if current_block_lines:
        text_content = "\n".join(current_block_lines).strip()
        if text_content:
            candidates.append({
                "question_number": current_q_num or "Intro/Header",
                "raw_block": text_content
            })
            
    # Prepend any header block text to the first actual question to preserve context
    if candidates and candidates[0]["question_number"] == "Intro/Header":
        intro = candidates.pop(0)
        if candidates:
            candidates[0]["raw_block"] = intro["raw_block"] + "\n" + candidates[0]["raw_block"]
        else:
            candidates.insert(0, intro)
            
    return candidates

def parse_questions_from_bank(raw_qb_text: str) -> List[dict]:
    """
    Sends the raw text of the question bank to the hybrid pre-parser to split into
    candidates, then uses Gemini to normalize and structure them without altering boundaries.
    """
    if not settings.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not configured in settings.")
        raise ValueError("Gemini API key is missing. Please configure GEMINI_API_KEY in your .env file.")
        
    if not raw_qb_text.strip():
        logger.warning("Empty raw question bank text provided for parsing.")
        return []
        
    logger.info("Splitting question bank text using deterministic pre-parser...")
    candidates = extract_candidate_blocks(raw_qb_text)
    
    # Fallback to direct Gemini parsing if no candidates could be identified
    if len(candidates) < 2:
        logger.warning("Deterministic pre-parser found fewer than 2 candidates. Falling back to direct LLM parsing.")
        prompt = f"""
You are an expert Exam Question Extractor and Normalizer.
Your goal is to parse raw text extracted from a College Question Bank, Homework sheet, or Past Year Questions (PYQ) document, and isolate every individual question.

CRITICAL PARSING RULES:
1. Detect and extract Top-Level Questions ONLY:
   - Identify top-level questions by their main numbering (e.g., "Question 1", "Question 2", "1.", "2.").
   - Do NOT create separate entries for sub-questions or multipart divisions.
2. Preserve multipart sub-questions inside the parent question:
   - Keep all subparts, options, and lists (e.g., "a)", "b)", "c)", "d)", "i)", "ii)", "1)", "2)") attached inside the parent question's `question_text` field.
3. Do NOT split schema instruction blocks, table structures, metadata headings, or schema titles into separate questions.
4. Handle OR Choices:
   - If Q3 and Q4 are separate top-level questions, extract BOTH as separate top-level questions.
5. Filter OCR Noise & Metadata:
   - Filter out page numbers, headers, footers, and general OCR artifacts.
6. Extract/Infer Marks:
   - Look for explicit marks indications in the text (e.g., "[10 marks]", "(5m)", "2 marks"). Keep clean text like "2 Marks", "5 Marks", "10 Marks".
   - If marks are not explicitly stated, infer the weight based on the question length, complexity, and verbs used.
7. Classify Question Type:
   - Classify the question into one of the following types: 'theory', 'definition', 'sql', 'relational_algebra', 'er_model', 'comparison', 'problem_solving', 'mixed'.
8. NO DEDUPLICATION:
   - Do NOT consolidate, group, or merge distinct numbered questions. Every numbered question must correspond to exactly one output.

RAW QUESTION BANK TEXT:
{raw_qb_text}
"""
    else:
        logger.info(f"Pre-parsed {len(candidates)} candidate blocks. Requesting Gemini refinement...")
        prompt = f"""
You are an expert Exam Question Refiner and Normalizer.
Your task is to take a list of pre-extracted candidate question blocks and normalize them into a structured output.

CRITICAL RULES:
1. PRESERVE BOUNDARIES: You must process each candidate block in the input list individually. You must return exactly one output question in the 'questions' list for each item in the input candidate blocks list. The output question count must be exactly {len(candidates)}.
2. NO MERGING OR SPLITTING: Do NOT merge adjacent question blocks, even if they are semantically similar. Do NOT split a candidate question block into multiple questions. Boundary modifications are strictly forbidden.
3. NORMALIZE TEXT: Clean up OCR errors, spelling mistakes, and formatting. Do not change the academic meaning of the question. Keep all subparts, options, tables, or code schemas inside the question text.
4. EXTRACT/INFER MARKS: Identify explicit marks (e.g. "[10 marks]", "5m", "2 Marks"). If marks are not explicitly stated, infer the weight based on the question wording and complexity. Output clean marks like "2 Marks", "5 Marks", "10 Marks".
5. CLASSIFY QUESTION TYPE: Classify the question into one of the following types:
   - 'theory': Conceptual questions requiring descriptive explanations.
   - 'definition': Brief definition of terms.
   - 'sql': Database query writing or SQL schema definitions.
   - 'relational_algebra': Relational algebra queries or expressions.
   - 'er_model': ER diagram descriptions, conversion to tables, schema mapping.
   - 'comparison': Differentiating or comparing two or more concepts.
   - 'problem_solving': Step-by-step math, normal form normalization, or algorithmic solving.
   - 'mixed': Questions containing a mixture of the above (e.g. part theory, part SQL query).

CANDIDATE QUESTION BLOCKS TO PROCESS:
{json.dumps(candidates, indent=2)}
"""

    try:
        parsed_data = generate_content_with_routing(
            prompt=prompt,
            response_schema=ParsedQuestionList,
            models=settings.QUESTION_PARSER_MODELS,
            pipeline_name="QUESTION_PARSER",
            temperature=0.1
        )
        logger.info(f"Successfully normalized {len(parsed_data.questions)} questions from question bank.")
        return [q.model_dump() for q in parsed_data.questions]
    except Exception as e:
        logger.error(f"Failed to parse questions from question bank: {str(e)}")
        raise RuntimeError(f"Failed to parse questions from question bank: {str(e)}") from e
