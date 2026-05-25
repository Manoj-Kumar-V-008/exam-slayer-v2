import copy
from jinja2 import Environment, FileSystemLoader
from markdown_it import MarkdownIt
from app.config import settings
from app.utils.logger import logger

def render_study_pack_html(study_pack: dict) -> str:
    """
    Parses semantic markdown in all user-visible study pack fields into HTML,
    pre-filtering all empty/whitespace-only list entries, then renders the
    pack using Jinja2. Passes absolute file URI path for image assets resolution.
    
    Args:
        study_pack: A dictionary representing the StudyPack.
        
    Returns:
        The rendered HTML string content.
    """
    logger.info("Starting Jinja2 template rendering for study pack with comprehensive markdown parsing...")
    try:
        # 1. Initialize MarkdownIt parser
        md = MarkdownIt("commonmark")
        
        # 2. Deep copy to avoid modifying original state dict
        processed_pack = copy.deepcopy(study_pack)
        
        # Helper to parse markdown and strip wrapping <p> tag for list items / clean inline tags
        def parse_md_inline(text: str) -> str:
            if not text or not isinstance(text, str):
                return ""
            rendered = md.render(text).strip()
            if rendered.startswith("<p>") and rendered.endswith("</p>"):
                rendered = rendered[3:-4]
            return rendered
        
        # 3. Parse markdown fields to HTML with strict filtering
        for section in processed_pack.get("sections", []):
            # Parse block markdown fields
            for field in ["summary", "simple_explanation", "exam_tip", "memory_trick"]:
                val = section.get(field)
                if val and isinstance(val, str):
                    section[f"{field}_html"] = md.render(val).strip()
                else:
                    section[f"{field}_html"] = ""
            
            # Parse list fields
            for list_field in [
                "key_points", "common_mistakes", "revision_cheatsheet", 
                "likely_questions_2_marks", "likely_questions_5_marks", "likely_questions_10_marks"
            ]:
                raw_items = section.get(list_field, [])
                if not raw_items or not isinstance(raw_items, list):
                    raw_items = []
                
                # Filter empty/whitespace-only list entries
                filtered_items = [
                    item for item in raw_items 
                    if item and isinstance(item, str) and item.strip()
                ]
                
                # Parse markdown for each clean item
                section[f"{list_field}_html"] = [parse_md_inline(item) for item in filtered_items]
            
        # 4. Load Jinja2 environment and render HTML
        env = Environment(loader=FileSystemLoader(str(settings.TEMPLATES_DIR)))
        template = env.get_template("study_pack.html")
        
        assets_dir_url = settings.ASSETS_DIR.resolve().as_uri()
        
        html_content = template.render(
            study_pack=processed_pack,
            assets_dir_url=assets_dir_url
        )
        logger.info("Successfully parsed markdown and rendered study pack HTML.")
        return html_content
        
    except Exception as e:
        logger.error(f"Failed to render study pack template: {str(e)}")
        raise e


def render_answer_pack_html(answer_pack: dict) -> str:
    """
    Parses semantic markdown in all user-visible answer pack fields into HTML,
    pre-filtering all empty/whitespace-only list entries, then renders the
    pack using Jinja2. Passes absolute file URI path for image assets resolution.
    
    Args:
        answer_pack: A dictionary representing the AnswerPack.
        
    Returns:
        The rendered HTML string content.
    """
    logger.info("Starting Jinja2 template rendering for answer pack with comprehensive markdown parsing...")
    try:
        # 1. Initialize MarkdownIt parser
        md = MarkdownIt("commonmark")
        
        # 2. Deep copy to avoid modifying original state dict
        processed_pack = copy.deepcopy(answer_pack)
        
        # Helper to parse markdown and strip wrapping <p> tag for list items / clean inline tags
        def parse_md_inline(text: str) -> str:
            if not text or not isinstance(text, str):
                return ""
            rendered = md.render(text).strip()
            if rendered.startswith("<p>") and rendered.endswith("</p>"):
                rendered = rendered[3:-4]
            return rendered
        
        # 3. Parse markdown fields to HTML with strict filtering
        for question in processed_pack.get("questions", []):
            # Parse block markdown fields
            for field in ["ideal_answer", "answer", "simple_explanation", "memory_trick"]:
                val = question.get(field)
                if val and isinstance(val, str):
                    question[f"{field}_html"] = md.render(val).strip()
                else:
                    question[f"{field}_html"] = ""
            
            # Parse list fields (revision_points)
            raw_items = question.get("revision_points", [])
            if not raw_items or not isinstance(raw_items, list):
                raw_items = []
            filtered_items = [
                item for item in raw_items 
                if item and isinstance(item, str) and item.strip()
            ]
            question["revision_points_html"] = [parse_md_inline(item) for item in filtered_items]

            # Parse list fields (quick_revision)
            raw_qr = question.get("quick_revision", [])
            if not raw_qr or not isinstance(raw_qr, list):
                raw_qr = []
            filtered_qr = [
                item for item in raw_qr 
                if item and isinstance(item, str) and item.strip()
            ]
            question["quick_revision_html"] = [parse_md_inline(item) for item in filtered_qr]
            
        # 4. Load Jinja2 environment and render HTML
        env = Environment(loader=FileSystemLoader(str(settings.TEMPLATES_DIR)))
        template = env.get_template("answer_pack.html")
        
        assets_dir_url = settings.ASSETS_DIR.resolve().as_uri()
        
        html_content = template.render(
            answer_pack=processed_pack,
            assets_dir_url=assets_dir_url
        )
        logger.info("Successfully parsed markdown and rendered answer pack HTML.")
        return html_content
        
    except Exception as e:
        logger.error(f"Failed to render answer pack template: {str(e)}")
        raise e
