from weasyprint import HTML
from pathlib import Path
from app.utils.logger import logger

def generate_pdf(html_content: str, output_path: Path, base_url: str = None) -> None:
    """
    Compiles self-contained HTML content into a premium PDF file using WeasyPrint.
    
    Args:
        html_content: The full rendered HTML string.
        output_path: Path representing where to save the generated PDF.
        base_url: Optional base URL for resolving relative assets (e.g. localhost URL).
    """
    logger.info(f"Generating PDF via WeasyPrint at output path: {output_path} with base_url={base_url}...")
    try:
        # WeasyPrint parses the HTML and saves the resulting document to disk
        HTML(string=html_content, base_url=base_url).write_pdf(target=str(output_path))
        logger.info(f"PDF successfully written to: {output_path}")
        
    except Exception as e:
        logger.error(f"WeasyPrint failed to compile PDF file: {str(e)}")
        raise e

