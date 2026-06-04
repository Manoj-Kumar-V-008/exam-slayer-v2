import sys
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent
sys.path.append(str(backend_dir))

from app.services.image_intelligence import (
    get_surrounding_text,
    calculate_relevance_score,
    place_images_in_answer,
    match_images_for_questions
)

def run_tests():
    print("=== RUNNING IMAGE INTELLIGENCE UNIT TESTS ===")
    
    # 1. Test get_surrounding_text
    test_text = "Before block text. {{IMAGE_ASSET:img_test.png}} After block text."
    surr = get_surrounding_text(test_text, "img_test.png", window_size=30)
    assert "Before" in surr and "After" in surr, f"Surrounding text extraction failed: '{surr}'"
    print("SUCCESS: surrounding text extraction test passed.")

    # 2. Test place_images_in_answer
    answer_markdown = """
### Overview
This is a general introduction.

### Three Schema Architecture
The DBMS three-schema architecture is crucial.

### Comparison
We compare options.
"""
    matched_images = [
        {
            "filename": "img_4.png",
            "caption": "Three Schema Architecture",
            "keywords": ["dbms", "external", "conceptual", "internal"],
            "image_type": "architecture",
            "surrounding_text": "DBMS internal conceptual external three schema architecture details."
        }
    ]
    
    placed = place_images_in_answer(answer_markdown, matched_images)
    # Check that img_4.png is placed right below the Three Schema Architecture heading
    placed_clean = " ".join(placed.split())
    assert "### Three Schema Architecture The DBMS three-schema architecture is crucial. {{IMAGE_ASSET:img_4.png}}" in placed_clean, f"Placeholder placement failed: {placed}"
    print("SUCCESS: programmatic placeholder placement in heading test passed.")

    # 3. Test calculate_relevance_score
    question_analysis = {
        "keywords": ["three schema", "conceptual", "external", "internal"],
        "subject_domain": "DBMS",
        "dominant_intent": "theory",
        "sub_intents": ["explanation"]
    }
    image_metadata = {
        "filename": "img_4.png",
        "caption": "Three Schema Architecture Diagram",
        "keywords": ["dbms", "external", "conceptual", "internal"],
        "image_type": "architecture",
        "surrounding_text": "This diagram illustrates the three schema architecture including the external, conceptual, and internal levels of database representation.",
        "educational_value": "high",
        "visual_weight": "heavy"
    }
    
    score = calculate_relevance_score("Explain the Three Schema Architecture of DBMS.", question_analysis, image_metadata)
    # The score should be quite high because of keyword overlap, subject matching, type boosts, etc.
    assert score > 15.0, f"Relevance score calculation lower than expected: {score}"
    print(f"SUCCESS: relevance score calculation test passed (Score: {score:.2f}).")

    # 4. Test match_images_for_questions with Explicit Diagram Mode
    parsed_questions = [
        {
            "question_number": "Question 1",
            "question_text": "Draw and explain the three schema architecture of a DBMS.",
            "likely_marks": "10 Marks",
            "dominant_intent": "theory",
            "sub_intents": ["diagram", "explanation"]
        }
    ]
    
    matched = match_images_for_questions(parsed_questions, [image_metadata])
    assert len(matched[0]["matched_images"]) == 1, "Failed to match image under Explicit Diagram mode"
    assert matched[0]["matched_images"][0]["filename"] == "img_4.png", "Matched wrong image filename"
    print("SUCCESS: match_images_for_questions matching test passed.")

    print("=== ALL IMAGE INTELLIGENCE UNIT TESTS PASSED ===")

if __name__ == "__main__":
    run_tests()
