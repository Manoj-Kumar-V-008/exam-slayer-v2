import time
from typing import List, Any
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

def generate_content_with_routing(
    prompt: str,
    response_schema: Any,
    models: List[str],
    pipeline_name: str,
    temperature: float = 0.2
) -> Any:
    """
    Executes content generation across a prioritized list of Gemini models.
    Supports quota limit detection (instant fallback), transient error retries on the same model,
    and cyclical retry backoff limits (max 3 cycles).
    """
    if not settings.GEMINI_API_KEY:
        logger.error(f"[{pipeline_name}] GEMINI_API_KEY is not configured in settings.")
        raise ValueError("Gemini API key is missing. Please configure GEMINI_API_KEY in your .env file.")

    if not models:
        logger.error(f"[{pipeline_name}] No models configured for routing.")
        raise ValueError(f"No models configured for pipeline: {pipeline_name}")

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    max_cycles = 3
    
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
                        contents=prompt,
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
            
    terminal_msg = f"[{pipeline_name}] terminal_failure: All models failed across all {max_cycles} cycles."
    logger.error(terminal_msg)
    raise RuntimeError(terminal_msg)
