import re
from typing import List
from app.utils.logger import logger

def clean_extracted_text(text: str) -> str:
    """
    Cleans extracted text to reduce token footprint while preserving academic content.
    - Removes duplicate whitespace/newlines.
    - Removes repetitive slide/page headers and footers.
    - Removes OCR artifacts and duplicate paragraphs/lines.
    - Trims redundant boilerplate sections (e.g. licensing).
    """
    if not text:
        return ""
    
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    lines = text.split('\n')
    cleaned_lines = []
    
    # Track unique lines to prevent duplicate paragraphs/duplicate headers/footers
    seen_paragraphs = set()
    
    # Compile regexes for common noise:
    page_patterns = [
        re.compile(r'(?i)^\s*page\s+\d+\s*(of\s*\d+)?\s*$'),
        re.compile(r'(?i)^\s*copyright\s*©.*$'),
        re.compile(r'(?i)^\s*all\s*rights\s*reserved.*$'),
        re.compile(r'(?i)^\s*http[s]?://\S+\s*$'), # Isolated URLs
    ]
    
    # OCR junk patterns (e.g. lines composed of only dashes, underscores, dots, or weird symbols)
    junk_patterns = [
        re.compile(r'^[\s\-_=\.\*\|#~]*$'), # Lines with only dividers/symbols
        re.compile(r'^[^a-zA-Z0-9\s\{\}]{4,}$'), # Lines with no words/letters (except asset placeholders)
    ]
    
    for line in lines:
        stripped_line = line.strip()
        if not stripped_line:
            cleaned_lines.append("")
            continue
            
        # Check for asset placeholders (must preserve them!)
        if "{{IMAGE_ASSET:" in stripped_line:
            cleaned_lines.append(stripped_line)
            continue
            
        # Filter page patterns
        if any(p.match(stripped_line) for p in page_patterns):
            continue
            
        # Filter OCR junk
        if any(j.match(stripped_line) for j in junk_patterns):
            continue
            
        # Filtering generic slides/page numbers that might just be digits
        if stripped_line.isdigit() and len(stripped_line) < 4:
            continue
            
        # Deduplicate redundant paragraphs/sentences (only deduplicate longer lines to avoid stripping list items)
        if len(stripped_line) > 40:
            normalized_line = " ".join(stripped_line.lower().split())
            if normalized_line in seen_paragraphs:
                # Skip duplicate long line
                continue
            seen_paragraphs.add(normalized_line)
            
        cleaned_lines.append(stripped_line)
        
    # Reconstruct text
    cleaned_text = "\n".join(cleaned_lines)
    
    # Clean up whitespace
    # Replace three or more consecutive newlines with two newlines
    cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
    # Replace multiple spaces with a single space (but preserve newlines)
    cleaned_text = re.sub(r'[ \t]+', ' ', cleaned_text)
    
    return cleaned_text.strip()

def compress_study_context_for_batch(
    study_text: str,
    batch_questions: List[dict],
    max_chars: int = 40000
) -> str:
    """
    Intelligently compresses the study_text to fit within max_chars.
    Priority preserved:
    - Definitions and key concepts
    - Formulas and equations
    - Image/diagram references
    - Paragraphs matching keywords from the current batch of questions
    """
    if not study_text:
        return ""
        
    if len(study_text) <= max_chars:
        return study_text

    logger.info(f"Study text length ({len(study_text)} chars) exceeds budget ({max_chars} chars). Running context compression...")

    # Extract keywords from batch questions to find relevant paragraphs
    keywords = set()
    for q in batch_questions:
        text = q.get("question_text", "").lower()
        # Simple keyword extraction: alphanumeric words of length >= 4, excluding common stop words
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text)
        # Exclude common academic/question stop words
        stop_words = {
            "what", "how", "why", "explain", "describe", "define", "discuss", "show", "write", "list", 
            "give", "with", "from", "each", "their", "them", "then", "than", "were", "been", "about",
            "question", "marks", "solved", "answer", "study", "material", "notes"
        }
        keywords.update(w for w in words if w not in stop_words)

    # Split study_text into logical paragraphs/blocks
    paragraphs = study_text.split('\n\n')
    
    # Grade each paragraph by relevance
    scored_paragraphs = []
    for idx, para in enumerate(paragraphs):
        score = 0
        para_lower = para.lower()
        
        # Rule 1: Contains formulas or equations
        if any(sym in para for sym in ["=", "+", "-", "*", "/", "λ", "θ", "≥", "≤", "->"]):
            score += 5
            
        # Rule 2: Contains image/diagram references
        if "{{IMAGE_ASSET:" in para:
            score += 8
            
        # Rule 3: Contains definition markers
        definition_markers = ["define", "definition", "is defined as", "refers to", "means", "concept of"]
        if any(marker in para_lower for marker in definition_markers):
            score += 4
            
        # Rule 4: Match keywords from the questions in the batch
        match_count = sum(1 for kw in keywords if kw in para_lower)
        score += match_count * 3
        
        # Rule 5: Keep headings (short lines in uppercase or starting with # or marked as slide/source headers)
        if len(para.strip()) < 80 and (para.strip().startswith('#') or para.strip().isupper() or "source file:" in para_lower):
            score += 6
            
        # Penalty for length (we prefer smaller, high-value paragraphs, but don't penalize too heavily if score is high)
        score -= min(len(para) / 1000.0, 1.5)
        
        scored_paragraphs.append((score, idx, para))
    
    # Sort by score descending
    scored_paragraphs.sort(key=lambda x: x[0], reverse=True)
    
    # Select paragraphs until we hit the max_chars limit
    selected_indices = set()
    current_len = 0
    
    for score, idx, para in scored_paragraphs:
        if current_len + len(para) + 2 <= max_chars:
            selected_indices.add(idx)
            current_len += len(para) + 2
        elif current_len >= max_chars * 0.8: # Already filled 80% of budget, stop to be safe
            break
            
    # Always ensure at least the top scored paragraphs are included even if one is large
    if not selected_indices and scored_paragraphs:
        selected_indices.add(scored_paragraphs[0][1])
        
    # Re-assemble selected paragraphs in their original order to preserve logical flow
    compressed_paragraphs = [paragraphs[i] for i in sorted(selected_indices)]
    compressed_text = "\n\n".join(compressed_paragraphs)
    
    logger.info(f"Compression complete: reduced context size from {len(study_text)} chars to {len(compressed_text)} chars.")
    
    # Add a compression note
    compression_note = f"\n\n[...Context compressed for size; preserved {len(selected_indices)}/{len(paragraphs)} key sections relevant to this question batch...]\n"
    return compressed_text + compression_note
