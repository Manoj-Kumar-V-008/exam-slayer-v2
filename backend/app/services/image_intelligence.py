import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from PIL import Image, ImageChops
from pathlib import Path
from app.config import settings
from app.utils.logger import logger
from google import genai
from google.genai import types

def crop_whitespace(image_path: Path) -> None:
    """Crops any unnecessary white border padding from an image using PIL."""
    try:
        with Image.open(image_path) as img:
            rgb_img = img.convert("RGB")
            # Create a solid white background image
            bg = Image.new("RGB", rgb_img.size, (255, 255, 255))
            # Find difference
            diff = ImageChops.difference(rgb_img, bg)
            # Get bounding box of difference
            bbox = diff.getbbox()
            if bbox:
                # Add a small 5px padding
                padding = 5
                xmin, ymin, xmax, ymax = bbox
                xmin = max(0, xmin - padding)
                ymin = max(0, ymin - padding)
                xmax = min(img.width, xmax + padding)
                ymax = min(img.height, ymax + padding)
                
                cropped = img.crop((xmin, ymin, xmax, ymax))
                cropped.save(image_path)
                logger.info(f"Cropped whitespace for {image_path.name}. New size: {cropped.size}")
            else:
                logger.info(f"Image {image_path.name} is fully white or blank. Skipping crop.")
    except Exception as e:
        logger.error(f"Failed to crop whitespace for {image_path}: {e}")

class ImageMetadata(BaseModel):
    filename: str = Field(..., description="The exact filename of the image.")
    caption: str = Field(..., description="A short, clear description of the image content/purpose.")
    keywords: List[str] = Field(default_factory=list, description="A list of 3-6 specific keywords or key concepts visible or discussed in the image.")
    image_type: str = Field(..., description="The type of academic image: 'architecture', 'flowchart', 'diagram', 'table', 'graph', 'ER model', 'network topology', 'process flow', 'screenshot', 'illustration', or 'other'.")
    surrounding_text: str = Field("", description="Programmatically extracted surrounding text from the document.")
    educational_value: str = Field(..., description="Educational value for exam prep: 'high', 'medium', or 'low'.")
    visual_weight: str = Field(..., description="Visual weight or complexity: 'heavy', 'medium', or 'light'.")

class QuestionAnalysis(BaseModel):
    keywords: List[str] = Field(..., description="3-6 key academic terms or entities in the question.")
    subject_domain: str = Field(..., description="The subject or domain of the question (e.g. 'DBMS', 'Operating Systems', 'Computer Networks').")

def get_surrounding_text(text: str, filename: str, window_size: int = 1000) -> str:
    """Programmatically extracts a window of text surrounding the image placeholder."""
    placeholder = f"{{{{IMAGE_ASSET:{filename}}}}}"
    idx = text.find(placeholder)
    if idx == -1:
        # Try matching just the filename
        idx = text.lower().find(filename.lower())
        if idx == -1:
            return ""
    
    start = max(0, idx - window_size)
    end = min(len(text), idx + len(placeholder) + window_size)
    return text[start:end].strip()

def generate_image_metadata_layer(job_id: str, assets: List[str], study_text: str) -> List[Dict[str, Any]]:
    """
    Generates metadata for every extracted image.
    Uses PIL to open files and Gemini's multimodal API to analyze details once.
    """
    if not assets:
        logger.info("No assets extracted. Skipping image metadata layer generation.")
        return []

    logger.info(f"Generating image metadata layer for {len(assets)} assets...")
    metadata_list = []
    
    # Initialize Google GenAI client
    if not settings.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not configured in settings.")
        return []
        
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    # We will use ANSWER_PACK_MODELS which contains Flash models capable of multimodal vision tasks
    models = settings.ANSWER_PACK_MODELS

    for filename in assets:
        image_path = settings.ASSETS_DIR / filename
        if not image_path.exists():
            logger.warning(f"Image path {image_path} does not exist. Skipping.")
            continue

        # Automatically crop whitespace to improve diagram quality
        crop_whitespace(image_path)

        surrounding = get_surrounding_text(study_text, filename)
        
        # Default fallback metadata
        fallback_meta = {
            "filename": filename,
            "caption": "Study notes diagram",
            "keywords": [],
            "image_type": "other",
            "surrounding_text": surrounding,
            "educational_value": "medium",
            "visual_weight": "medium"
        }

        try:
            img = Image.open(image_path)
            
            prompt = f"""
            You are an expert academic image analyzer.
            Analyze the provided image in the context of the surrounding source text from the lecture notes/study material.

            === SURROUNDING SOURCE TEXT ===
            {surrounding}

            Provide:
            1. A concise, clear caption for the image (e.g. 'Three Schema Architecture', 'ER Diagram for University Database').
            2. A list of 3-6 specific academic keywords or key concepts visible in the image or discussed around it.
            3. The image type. It must be exactly one of: 'architecture', 'flowchart', 'diagram', 'table', 'graph', 'ER model', 'network topology', 'process flow', 'screenshot', 'illustration', 'other'.
            4. The educational value of this image for a student preparing for exams. It must be exactly one of: 'high' (contains critical conceptual architecture, equations, tables, flowcharts, or diagrams), 'medium' (helpful visualization of concepts, example screenshots, simple tables), or 'low' (decorative icon, slide header graphic, minimal text, bullet graphic of little academic value).
            5. The visual weight/complexity of the image. It must be exactly one of: 'heavy' (highly complex architecture diagram, detailed flowchart, large table), 'medium' (simple diagram, small table, state flowchart), or 'light' (small icon, simple formula, bullet point illustration).
            """
            
            parsed_result = None
            for model in models:
                try:
                    logger.info(f"Analyzing {filename} with multimodal model '{model}'...")
                    response = client.models.generate_content(
                        model=model,
                        contents=[img, prompt],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=ImageMetadata,
                            temperature=0.2
                        )
                    )
                    if response.text:
                        parsed_result = ImageMetadata.model_validate_json(response.text)
                        break
                except Exception as e:
                    logger.warning(f"Model '{model}' failed to analyze image {filename}: {e}")
                    continue
            
            if parsed_result:
                metadata_list.append({
                    "filename": filename,
                    "caption": parsed_result.caption,
                    "keywords": [k.lower().strip() for k in parsed_result.keywords if k],
                    "image_type": parsed_result.image_type.lower().strip(),
                    "surrounding_text": surrounding,
                    "educational_value": parsed_result.educational_value.lower().strip(),
                    "visual_weight": parsed_result.visual_weight.lower().strip()
                })
                logger.info(f"Successfully generated metadata for image {filename}: Type='{parsed_result.image_type}', EdValue='{parsed_result.educational_value}'")
            else:
                logger.warning(f"All models failed for image {filename}. Using fallback.")
                metadata_list.append(fallback_meta)
                
        except Exception as ex:
            logger.error(f"Error processing image {filename}: {ex}. Using fallback.")
            metadata_list.append(fallback_meta)

    return metadata_list

def analyze_question(question_text: str) -> Dict[str, Any]:
    """Extracts keywords and subject domain from a question using Gemini."""
    if not settings.GEMINI_API_KEY:
        return {"keywords": [], "subject_domain": "unknown"}
        
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    models = settings.QUESTION_PARSER_MODELS
    
    prompt = f"""
    Analyze the following exam question and extract:
    1. A list of 3-6 specific academic keywords or key concepts.
    2. The subject or domain of the question (e.g. 'DBMS', 'Operating Systems', 'Computer Networks', 'Algorithms', 'Mathematics').

    === QUESTION TEXT ===
    {question_text}
    """
    
    for model in models:
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=QuestionAnalysis,
                    temperature=0.1
                )
            )
            if response.text:
                parsed = QuestionAnalysis.model_validate_json(response.text)
                return {
                    "keywords": [k.lower().strip() for k in parsed.keywords if k],
                    "subject_domain": parsed.subject_domain.strip()
                }
        except Exception as e:
            logger.warning(f"Failed to analyze question with model '{model}': {e}")
            continue
            
    return {"keywords": [], "subject_domain": "unknown"}

def calculate_relevance_score(question_text: str, question_analysis: Dict[str, Any], image: Dict[str, Any]) -> float:
    """
    Programmatic, deterministic scoring function combining keywords,
    Jaccard word similarity, subject alignment, type matching, and visual value.
    """
    score = 0.0
    
    q_text_lower = question_text.lower()
    img_surrounding_lower = image.get("surrounding_text", "").lower()
    img_caption_lower = image.get("caption", "").lower()
    img_keywords = [k.lower().strip() for k in image.get("keywords", [])]
    
    # 1. Keyword overlap
    q_kws = set(question_analysis.get("keywords", []))
    img_kws = set(img_keywords)
    overlap = q_kws.intersection(img_kws)
    score += len(overlap) * 3.5  # Heavy weight for matching exact keywords
    
    # Overlap with caption
    for kw in q_kws:
        if kw in img_caption_lower:
            score += 2.0
            
    # 2. Subject similarity
    subject = question_analysis.get("subject_domain", "").lower()
    if subject != "unknown":
        if subject in img_surrounding_lower or subject in img_caption_lower:
            score += 2.5
            
    # 3. Jaccard word similarity on text content (4+ letter words)
    q_words = set(re.findall(r'\b\w{4,}\b', q_text_lower))
    img_words = set(re.findall(r'\b\w{4,}\b', img_surrounding_lower))
    jaccard = 0.0
    if q_words and img_words:
        jaccard = len(q_words.intersection(img_words)) / len(q_words.union(img_words))
        score += jaccard * 10.0  # Up to 10 points
        
    # Conceptual Overlap Guard:
    # If there is 0 keyword overlap, 0 Jaccard similarity, and no caption word overlap, force score to 0.0
    has_kw_overlap = len(overlap) > 0
    has_jaccard_overlap = jaccard > 0.01
    has_caption_match = any(word in q_text_lower for word in img_caption_lower.split() if len(word) >= 4)
    
    if not (has_kw_overlap or has_jaccard_overlap or has_caption_match):
        logger.debug(f"Zero conceptual overlap guard triggered for image '{image.get('filename')}' on question '{question_text[:50]}...'. Forcing score to 0.0.")
        return 0.0
        
    # 4. Image type and dominant intent relevance
    img_type = image.get("image_type", "").lower()
    dom_intent = question_analysis.get("dominant_intent", "").lower()
    
    # Explicit mapping offsets
    type_indicators = {
        "er model": ["er model", "er diagram", "entity relationship", "entity-relationship", "schema mapping"],
        "architecture": ["architecture", "structure", "component", "layer", "three schema", "three-schema"],
        "process flow": ["process flow", "flowchart", "sequence flow", "steps", "workflow"],
        "flowchart": ["flowchart", "flow", "workflow", "algorithm steps"],
        "network topology": ["network", "topology", "routing", "lan", "wan", "subnet", "bus", "star", "ring"],
        "table": ["table", "comparison", "difference", "distinguish", "vs", "versus"],
        "graph": ["graph", "plot", "chart", "complexity curve"]
    }
    
    for t_type, words in type_indicators.items():
        if any(w in q_text_lower for w in words):
            if img_type == t_type:
                score += 5.0  # Match booster
            elif t_type == "process flow" and img_type == "flowchart":
                score += 4.0  # Close match
                
    if dom_intent == "er_model" and img_type == "er model":
        score += 4.0
    elif dom_intent == "sql" and img_type in ["table", "diagram"]:
        score += 2.0
    elif dom_intent == "comparison" and img_type == "table":
        score += 3.0
        
    # 5. Educational value & visual weight boosts
    ed_val = image.get("educational_value", "").lower()
    if ed_val == "high":
        score += 1.5
    elif ed_val == "medium":
        score += 0.5
        
    vis_weight = image.get("visual_weight", "").lower()
    if vis_weight == "heavy":
        score += 1.0
    elif vis_weight == "medium":
        score += 0.5
        
    return score

def gemini_tie_breaker(question_text: str, tied_images: List[Dict[str, Any]]) -> str:
    """Uses Gemini as a tie-breaker to choose between images with identical top scores."""
    if not settings.GEMINI_API_KEY or not tied_images:
        return tied_images[0]["filename"] if tied_images else ""
        
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    models = settings.QUESTION_PARSER_MODELS
    
    logger.info(f"TIE BREAKER: {len(tied_images)} images tied for question '{question_text[:50]}...'. Asking Gemini...")
    
    images_list = []
    for img in tied_images:
        images_list.append({
            "filename": img["filename"],
            "caption": img["caption"],
            "keywords": img["keywords"],
            "image_type": img["image_type"]
        })
        
    prompt = f"""
    A student has asked the following exam question.
    Two or more diagrams from the lecture notes have scored equally in our relevance matching system.
    Choose the ONE diagram that is MOST helpful and directly explains the concepts in this specific question.
    
    === EXAM QUESTION ===
    {question_text}
    
    === TIED DIAGRAMS ===
    {images_list}
    
    Return ONLY a JSON object with a single field:
    "selected_filename": "the_filename_of_the_chosen_diagram"
    """
    
    class Selection(BaseModel):
        selected_filename: str
        
    for model in models:
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=Selection,
                    temperature=0.1
                )
            )
            if response.text:
                parsed = Selection.model_validate_json(response.text)
                chosen = parsed.selected_filename
                # Verify it is one of the tied filenames
                if any(img["filename"] == chosen for img in tied_images):
                    logger.info(f"Tie breaker selected '{chosen}'")
                    return chosen
        except Exception as e:
            logger.warning(f"Tie breaker failed on model '{model}': {e}")
            continue
            
    # Default fallback
    logger.info(f"Tie breaker fallback to first image '{tied_images[0]['filename']}'")
    return tied_images[0]["filename"]

def match_images_for_questions(parsed_questions: List[Dict[str, Any]], image_metadata_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Orchestrates the matching of images to questions.
    Applies attachment rules (Explicit Diagram Required vs Helpful Visualization) and mark-based limits.
    """
    if not image_metadata_list:
        logger.info("No images available to match.")
        for q in parsed_questions:
            q["matched_images"] = []
            q["related_assets"] = []
        return parsed_questions

    logger.info(f"Matching {len(image_metadata_list)} images against {len(parsed_questions)} questions...")
    matched_questions = []
    
    # Keep track of how many times each image is matched across the entire pack
    image_usage_counts = {}

    for q in parsed_questions:
        q_text = q.get("question_text", "")
        q_text_lower = q_text.lower()
        marks = q.get("likely_marks", "") or ""
        
        # 1. Question analysis
        q_analysis = analyze_question(q_text)
        # Merge parsed question properties
        q_analysis["dominant_intent"] = q.get("dominant_intent", "theory")
        q_analysis["sub_intents"] = q.get("sub_intents", [])
        
        # 2. Determine attachment mode
        diagram_keywords = ["diagram", "figure", "draw", "illustrate", "architecture", "workflow", "topology", "schema", "flowchart", "er model", "er diagram"]
        is_explicit = any(w in q_text_lower for w in diagram_keywords)
        mode = "Explicit Diagram Required" if is_explicit else "Helpful Visualization"
        
        # 3. Calculate scores
        candidate_scores = []
        for img in image_metadata_list:
            score = calculate_relevance_score(q_text, q_analysis, img)
            candidate_scores.append((score, img))
            
        # Sort by score descending
        candidate_scores.sort(key=lambda x: x[0], reverse=True)
        
        # 4. Filter based on Mode & Confidence Rules
        attached = []
        
        # Check Low Confidence exclusions:
        # - purely definitional, comparison, or advantages/disadvantages question
        sub_intents_lower = [s.lower() for s in q.get("sub_intents", [])]
        dom_intent_lower = q.get("dominant_intent", "").lower()
        
        is_definition = dom_intent_lower == "definition" or "definition" in sub_intents_lower
        is_comparison = dom_intent_lower == "comparison" or "comparison" in sub_intents_lower
        is_pros_cons = "advantages" in sub_intents_lower or "disadvantages" in sub_intents_lower or any(kw in q_text_lower for kw in ["advantage", "disadvantage", "pro", "con", "benefit", "drawback"])
        
        is_low_confidence_q = (is_definition or is_comparison or is_pros_cons)
        
        # High-marks exception: 10 marks are never considered low-confidence to encourage visual enrichment
        is_10_marks = "10" in marks
        if is_10_marks:
            is_low_confidence_q = False

        # Apply limits: max 2 for 2-mark, 3 for 5-mark, 4 for 10-mark
        max_images = 2
        if "10" in marks:
            max_images = 4
        elif "5" in marks:
            max_images = 3
        elif "2" in marks:
            max_images = 2

        # Process matching
        logger.debug(f"Question '{q.get('question_number')}' is in Mode='{mode}' (LowConf={is_low_confidence_q}, MaxImgs={max_images})")
        
        temp_candidates = []
        for score, img in candidate_scores:
            # Image Reuse Spam Prevention
            # Limit: at most 1 question, or at most 2 questions if score is >= 15.0 (exceptionally high match)
            filename = img["filename"]
            usage = image_usage_counts.get(filename, 0)
            max_allowed = 2 if score >= 15.0 else 1
            if usage >= max_allowed:
                logger.debug(f"Skipping image {filename} for question '{q.get('question_number')}' - reached reuse limit ({usage}/{max_allowed})")
                continue
                
            if mode == "Explicit Diagram Required":
                # Lower threshold for explicit diagrams
                if score >= 5.0:
                    temp_candidates.append((score, img))
            else:  # Helpful Visualization mode
                # Higher threshold, skip low confidence questions, filter out low educational values
                if score >= 7.5 and not is_low_confidence_q:
                    if img.get("educational_value") != "low":
                        temp_candidates.append((score, img))
                        
        # Handle Tie-breaker if multiple images have the same top score
        final_list = []
        while temp_candidates and len(final_list) < max_images:
            top_score = temp_candidates[0][0]
            # Find all tied with top_score
            tied = [c for c in temp_candidates if c[0] == top_score]
            if len(tied) > 1 and len(final_list) + len(tied) > max_images:
                # Need to break ties
                chosen_filename = gemini_tie_breaker(q_text, [c[1] for c in tied])
                # Find that item
                for idx, c in enumerate(tied):
                    if c[1]["filename"] == chosen_filename:
                        final_list.append(c[1])
                        temp_candidates.remove(c)
                        break
            else:
                for c in tied:
                    final_list.append(c[1])
                    temp_candidates.remove(c)
                    if len(final_list) >= max_images:
                        break
                        
        q["matched_images"] = final_list
        q["related_assets"] = [img["filename"] for img in final_list]
        
        # Record image usage
        for img in final_list:
            image_usage_counts[img["filename"]] = image_usage_counts.get(img["filename"], 0) + 1
            
        logger.info(f"Question '{q.get('question_number')}' matched with {len(final_list)} images: {[img['filename'] for img in final_list]}")
        matched_questions.append(q)

    return matched_questions

def place_images_in_answer(answer_markdown: str, matched_images: List[Dict[str, Any]]) -> str:
    """
    Parses answer markdown, splits by subsection headings, and programmatically
    injects image placeholders directly below the most relevant subsection heading.
    """
    if not matched_images:
        return answer_markdown

    # Split the answer by markdown headings (e.g. ## or ###)
    pattern = re.compile(r'^(#+\s+.*)$', re.MULTILINE)
    parts = pattern.split(answer_markdown)
    
    if len(parts) <= 1:
        # No headings. Just append all image placeholders at the end of the text.
        res = answer_markdown
        for img in matched_images:
            res += f"\n\n{{{{IMAGE_ASSET:{img['filename']}}}}}\n\n"
        return res

    # Construct sections list
    sections = []
    sections.append({
        "heading": "",
        "content": parts[0],
        "full_text": parts[0]
    })
    
    for i in range(1, len(parts), 2):
        heading = parts[i]
        content = parts[i+1] if i+1 < len(parts) else ""
        sections.append({
            "heading": heading,
            "content": content,
            "full_text": heading + "\n" + content
        })

    # Place each image in the best matching heading
    for img in matched_images:
        best_idx = 0
        best_score = -1.0
        
        for idx, sec in enumerate(sections):
            if idx == 0 and sec["heading"] == "":
                if len(sections) > 1:
                    continue  # Prefer matching a heading section
                    
            # Compute a matching score for this section
            score = 0.0
            heading_clean = re.sub(r'^#+\s+', '', sec["heading"]).lower()
            content_clean = sec["content"].lower()
            caption_clean = img["caption"].lower()
            keywords = [k.lower() for k in img.get("keywords", [])]
            
            # Exact/partial caption overlap in heading
            if caption_clean in heading_clean or heading_clean in caption_clean:
                score += 10.0
            else:
                h_words = set(re.findall(r'\b\w{3,}\b', heading_clean))
                c_words = set(re.findall(r'\b\w{3,}\b', caption_clean))
                if h_words and c_words:
                    score += len(h_words.intersection(c_words)) * 2.0
                    
            # Keywords overlap
            for kw in keywords:
                if kw in heading_clean:
                    score += 3.0
                if kw in content_clean:
                    score += 1.0
                    
            # Text similarity
            sec_words = set(re.findall(r'\b\w{4,}\b', sec["full_text"].lower()))
            orig_words = set(re.findall(r'\b\w{4,}\b', img.get("surrounding_text", "").lower()))
            if sec_words and orig_words:
                score += len(sec_words.intersection(orig_words)) * 0.2
                
            if score > best_score:
                best_score = score
                best_idx = idx

        # Insert placeholder
        best_sec = sections[best_idx]
        img_placeholder = f"\n\n{{{{IMAGE_ASSET:{img['filename']}}}}}\n\n"
        
        # Programmatic injection directly after the section content (placing diagrams after text explanations)
        best_sec["content"] = best_sec["content"] + img_placeholder
        best_sec["full_text"] = best_sec["heading"] + "\n" + best_sec["content"]

    # Reconstruct final markdown
    reconstructed = []
    for sec in sections:
        if sec["heading"]:
            reconstructed.append(sec["heading"])
        if sec["content"]:
            reconstructed.append(sec["content"])
            
    return "\n".join(reconstructed)
