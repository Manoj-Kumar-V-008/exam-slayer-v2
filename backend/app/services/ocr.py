from pathlib import Path
from typing import List

from PIL import Image
from app.config import settings
from app.utils.logger import logger


class OCRService:
    """
    Lazy-initializing OCR service backed by Tesseract via pytesseract.

    The public interface intentionally stays the same as the previous OCR
    backend so the Stage 6 extractor integration can remain unchanged.
    """

    _configured = False
    _pytesseract = None

    @classmethod
    def _get_engine(cls):
        """Lazily imports and validates pytesseract/Tesseract on first use."""
        if cls._configured:
            return cls._pytesseract

        logger.info("Initializing Tesseract OCR engine...")
        try:
            import pytesseract
            from pytesseract import TesseractNotFoundError

            if settings.TESSERACT_CMD:
                pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
                logger.info(f"Using configured Tesseract binary: {settings.TESSERACT_CMD}")

            version = pytesseract.get_tesseract_version()
            logger.info(f"Tesseract OCR engine initialised successfully. Version: {version}")

            cls._pytesseract = pytesseract
            cls._configured = True
            return cls._pytesseract
        except ImportError as exc:
            message = (
                "pytesseract is not installed. Install Python dependencies with "
                "`pip install -r requirements.txt` from the backend directory."
            )
            logger.error(message)
            raise RuntimeError(message) from exc
        except TesseractNotFoundError as exc:
            message = (
                "Tesseract executable was not found. Install Tesseract OCR for Windows "
                "and either add it to PATH or set TESSERACT_CMD in .env."
            )
            logger.error(message)
            raise RuntimeError(message) from exc
        except Exception as exc:
            logger.error(f"Failed to initialise Tesseract OCR engine: {exc}")
            raise

    @classmethod
    def extract_text_from_images(cls, image_paths: List[Path]) -> str:
        """
        Runs OCR over image_paths in order and returns the combined text.

        Pages are separated by blank lines. A single image failure is logged and
        processing continues; RuntimeError is raised only if every image fails.
        """
        if not image_paths:
            return ""

        pytesseract = cls._get_engine()
        page_texts: List[str] = []
        successful_runs = 0

        for idx, img_path in enumerate(image_paths):
            img_path = Path(img_path)
            logger.info(f"Running OCR on image {idx + 1}/{len(image_paths)}: {img_path}")

            try:
                if not img_path.exists():
                    raise FileNotFoundError(f"OCR image not found: {img_path}")

                with Image.open(img_path) as image:
                    text = pytesseract.image_to_string(image, lang="eng")

                successful_runs += 1
                clean_text = text.strip()
                if clean_text:
                    page_texts.append(clean_text)
                    line_count = len([line for line in clean_text.splitlines() if line.strip()])
                    logger.info(f"OCR image {idx + 1}: extracted {line_count} text line(s).")
                else:
                    logger.warning(f"No text detected in image: {img_path}")

            except Exception as exc:
                logger.warning(f"OCR failed for image {img_path}: {exc}")

        if successful_runs == 0 and image_paths:
            logger.error("OCR extraction failed completely - no images processed successfully.")
            raise RuntimeError("Tesseract OCR processing failed completely for all images.")

        return "\n\n".join(page_texts)
