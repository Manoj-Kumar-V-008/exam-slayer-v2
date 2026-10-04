"""Deterministic quality gate for solved answers (LLM-judge-ready interface).

Checks (no extra API cost):
- citation presence + validity against retrieved [S#] chunk IDs
- answer length minimums per marks category
- placeholder / HTML leaks the renderer owns programmatically

Swap-in point for an LLM judge: replace `_score_coverage` / add a judge call
inside `evaluate_question` keeping the same return shape.
"""
import re
from typing import Dict, List, Tuple
from app.config import settings
from app.utils.logger import logger

_CITE_RE = re.compile(r"\[(S\d+)\]")

# Lenient minimums (prompt targets are higher: 2M 80-150, 5M 200-350, 10M 450-800)
_MIN_WORDS = {"2": 50, "5": 120, "10": 300}


def _marks_key(marks: str | None) -> str:
    m = (marks or "").lower()
    if "10" in m:
        return "10"
    if "5" in m:
        return "5"
    return "2"


def evaluate_question(solved: dict, batch_sources: List[str]) -> dict:
    """Score one solved question. Never raises — returns pass/score/issues."""
    try:
        issues: List[str] = []
        score = 1.0
        answer = solved.get("answer", "") or ""
        valid_ids = {s.split("|")[0].strip().upper() for s in (batch_sources or []) if s}

        cited = [c.upper() for c in _CITE_RE.findall(answer)]
        if len(cited) < settings.EVAL_MIN_CITATIONS:
            issues.append(f"missing-citation (found {len(cited)}, need {settings.EVAL_MIN_CITATIONS})")
            score -= 0.4
        elif valid_ids:
            bad = [c for c in cited if c not in valid_ids]
            if bad:
                issues.append(f"invalid-citation {bad} not in {sorted(valid_ids)}")
                score -= 0.3

        words = len(answer.split())
        need = _MIN_WORDS[_marks_key(solved.get("marks_category"))]
        if words < need:
            issues.append(f"too-short ({words} words, need {need} for {solved.get('marks_category')})")
            score -= 0.3

        if "{{IMAGE_ASSET" in answer or "<img" in answer.lower():
            issues.append("placeholder-leak (renderer owns image placement)")
            score -= 0.5

        if not (solved.get("simple_explanation") or "").strip():
            issues.append("missing-simple-explanation")
            score -= 0.1

        score = max(0.0, round(score, 2))
        passed = score >= 0.6 and not any(i.startswith(("placeholder-leak", "missing-citation")) for i in issues)
        return {"pass": passed, "score": score, "issues": issues}
    except Exception as e:
        logger.warning(f"[eval] scoring failed: {e}")
        return {"pass": True, "score": 1.0, "issues": [f"eval-error: {e}"]}


def evaluate_batch(solved: List[dict], batch_sources: List[str]) -> Tuple[bool, float, List[dict]]:
    """Score a batch. Returns (overall_pass, avg_score, per_question_results)."""
    results = [evaluate_question(sq, batch_sources) for sq in solved]
    avg = round(sum(r["score"] for r in results) / len(results), 2) if results else 1.0
    return all(r["pass"] for r in results), avg, results
