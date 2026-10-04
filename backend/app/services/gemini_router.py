import time
from pathlib import Path
from typing import List, Any, Optional, Union
from google import genai
from google.genai import types
from app.config import settings
from app.utils.logger import logger

def _is_quota_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    quota_markers = [
        "429",
        "quota",
        "rate limit",
        "rate-limit",
        "resource_exhausted",
        "too many requests"
    ]
    return any(m in msg for m in quota_markers)

def _is_transient_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    transient_markers = [
        "timeout",
        "timed out",
        "temporarily unavailable",
        "unavailable",
        "503",
        "502",
        "500",
        "504",
        "getaddrinfo",
        "connection",
        "socket",
        "dns",
        "network",
        "unreachable",
    ]
    return any(m in msg for m in transient_markers)

def _build_vision_parts(vision_images: Optional[List[Union[str, Path, bytes]]]):
    """Load vision images as Gemini Parts. Skips unreadable files, never raises."""
    if not vision_images:
        return []
    parts = []
    for item in vision_images:
        try:
            if isinstance(item, bytes):
                data, mime = item, "image/jpeg"
            else:
                p = Path(str(item))
                if not p.exists():
                    logger.warning(f"[vision] skipping missing image: {p}")
                    continue
                data = p.read_bytes()
                mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
            if not data:
                continue
            parts.append(types.Part.from_bytes(data=data, mime_type=mime))
        except Exception as e:
            logger.warning(f"[vision] skipping unloadable image {item}: {e}")
            continue
    return parts


def generate_content_with_routing(
    prompt: str,
    response_schema: Any,
    models: List[str],
    pipeline_name: str,
    temperature: float = 0.2,
    vision_images: Optional[List[Union[str, Path, bytes]]] = None,
) -> Any:
    """
    Executes content generation across a prioritized list of Gemini models.
    Supports quota limit detection (instant fallback), transient error retries on the same model,
    and cyclical retry backoff limits (max 3 cycles).
    When vision_images are provided, sends [prompt, *image_parts] multimodally;
    otherwise sends text-only (backward compatible).
    """
    if not settings.GEMINI_API_KEY:
        logger.error(f"[{pipeline_name}] GEMINI_API_KEY is not configured in settings.")
        raise ValueError("Gemini API key is missing. Please configure GEMINI_API_KEY in your .env file.")

    if not models:
        logger.error(f"[{pipeline_name}] No models configured for routing.")
        raise ValueError(f"No models configured for pipeline: {pipeline_name}")

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    max_cycles = 3
    last_error: Exception | None = None
    last_model: str = ""
    vision_parts = _build_vision_parts(vision_images)
    if vision_parts:
        logger.info(f"[{pipeline_name}] vision_enabled with {len(vision_parts)} page render(s).")
    contents: Any = [prompt, *vision_parts] if vision_parts else prompt
    
    for cycle in range(1, max_cycles + 1):
        logger.info(f"[{pipeline_name}] Starting model routing cycle {cycle}/{max_cycles}...")
        
        for model_idx, model in enumerate(models):
            logger.info(f"[{pipeline_name}] selected_model='{model}' (index={model_idx})")
            
            # Max attempts per model per cycle on transient non-quota errors
            max_model_attempts = 2
            for attempt in range(1, max_model_attempts + 1):
                try:
                    logger.info(
                        f"[{pipeline_name}] Requesting generation from '{model}' "
                        f"(attempt={attempt}/{max_model_attempts}, cycle={cycle}/{max_cycles})..."
                    )
                    
                    response = client.models.generate_content(
                        model=model,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=response_schema,
                            temperature=temperature
                        )
                    )
                    
                    raw_response_text = response.text
                    if not raw_response_text:
                        raise ValueError("Received an empty response from Gemini API.")
                        
                    validated_data = response_schema.model_validate_json(raw_response_text)
                    logger.info(f"[{pipeline_name}] success_model='{model}' on cycle={cycle}")
                    return validated_data
                    
                except Exception as e:
                    error_msg = str(e)
                    last_error = e
                    last_model = model
                    
                    # 1. Quota Exhaustion -> Switch immediately
                    if _is_quota_error(e):
                        logger.warning(
                            f"[{pipeline_name}] quota_exhaustion on model '{model}'. Error: {error_msg}. "
                            f"Action: fallback_switch to next model."
                        )
                        break
                        
                    # 2. Other Transient Errors -> Retry same model first
                    elif _is_transient_error(e):
                        if attempt < max_model_attempts:
                            delay = 5 * attempt
                            logger.warning(
                                f"[{pipeline_name}] transient_failure on model '{model}': {error_msg}. "
                                f"Action: Retrying same model in {delay}s..."
                            )
                            time.sleep(delay)
                            continue
                        else:
                            logger.warning(
                                f"[{pipeline_name}] transient_failures_exhausted on model '{model}'. "
                                f"Action: Proceeding to fallback model."
                            )
                            break
                            
                    # 3. Permanent or Validation Errors -> Fallback immediately
                    else:
                        logger.warning(
                            f"[{pipeline_name}] model_failure on '{model}': {error_msg}. "
                            f"Action: Proceeding to fallback model."
                        )
                        break
                        
        if cycle < max_cycles:
            backoff_delay = cycle * 10
            logger.warning(
                f"[{pipeline_name}] Cycle {cycle} exhausted. All configured models failed in this cycle. "
                f"Action: Applying exponential backoff of {backoff_delay}s before starting cycle {cycle + 1}..."
            )
            time.sleep(backoff_delay)
            
    terminal_msg = (
        f"[{pipeline_name}] terminal_failure: All models failed across all {max_cycles} cycles. "
        f"Tried {models}. Last failure on '{last_model}': {last_error}"
    )
    logger.error(terminal_msg)
    raise RuntimeError(terminal_msg) from last_error
