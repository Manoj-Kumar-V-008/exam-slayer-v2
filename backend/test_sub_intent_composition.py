import sys
import os
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent
sys.path.append(str(backend_dir))

from app.config import settings
from app.services.question_parser import parse_questions_from_bank
from app.services.ai import generate_solved_answers

def count_words(text: str) -> int:
    import re
    # Clean markdown formatting to get a more accurate word count
    clean_text = re.sub(r"[#\*_`\-\|]", " ", text)
    return len(clean_text.split())

def run_sub_intent_tests():
    print("=== RUNNING SUB-INTENT DECOMPOSITION VALIDATION ===")
    
    # 1. Verify GEMINI_API_KEY
    if not settings.GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY is not configured in settings.")
        sys.exit(1)
        
    # 2. Define test questions (mixed-intent)
    raw_qb_text = """
1. Define normalization and differentiate between 2NF and 3NF with examples. [10 Marks]
2. Write a SQL query to find the second highest salary in the Employee table and explain how it works. [5 Marks]
3. Explain the steps to map an ER model to relational tables and list advantages. [10 Marks]
4. Draw and explain a diagram showing the architecture of a 3-tier database system. [5 Marks]
"""

    study_text = """
=== Normalization & Normal Forms ===
Normalization is the process of organizing data in a database to reduce redundancy and improve data integrity. 
Second Normal Form (2NF): A table is in 2NF if it is in 1NF and all non-key attributes are fully functionally dependent on the primary key (no partial dependency). For example, in a table with composite key (OrderID, ProductID), any attribute dependent only on ProductID is a partial dependency.
Third Normal Form (3NF): A table is in 3NF if it is in 2NF and no non-transitive dependency exists (no non-key attribute is dependent on another non-key attribute). For example, if BookID -> AuthorID and AuthorID -> AuthorNationality, Nationality depends transitively on BookID.

=== SQL Employee Queries ===
To find the second highest salary, we can query:
SELECT MAX(Salary) FROM Employee WHERE Salary < (SELECT MAX(Salary) FROM Employee);
Another way is using LIMIT/OFFSET:
SELECT Salary FROM Employee ORDER BY Salary DESC LIMIT 1 OFFSET 1;

=== ER Model to Relational Mapping ===
Mapping steps:
1. Map strong entity types: Create a relation containing all simple attributes.
2. Map weak entity types: Create a relation including owner primary key as foreign key.
3. Map 1:1 binary relationship types: Add foreign key to one relation.
4. Map 1:N binary relationship types: Add primary key of 1-side as foreign key to N-side.
5. Map M:N relationship types: Create a cross-reference relation with primary keys of both sides.
Advantages: Clear structure, preserves integrity, easy SQL generation.

=== 3-Tier Database Architecture ===
The 3-tier architecture contains:
1. Presentation tier: User interface (web/app client).
2. Application/Business logic tier: Serves data requests, runs business rules.
3. Database/Data tier: RDBMS storing physical data.
"""

    print("\n--- Parsing Questions ---")
    try:
        parsed_questions = parse_questions_from_bank(raw_qb_text)
        print(f"Parsed {len(parsed_questions)} questions:")
        for idx, q in enumerate(parsed_questions, 1):
            print(f"\nQuestion {idx}:")
            print(f"  Number: {q.get('question_number')}")
            print(f"  Text: {q.get('question_text')[:60]}...")
            print(f"  Dominant Intent: {q.get('dominant_intent')}")
            print(f"  Sub-Intents: {q.get('sub_intents')}")
            print(f"  Likely Marks: {q.get('likely_marks')}")
    except Exception as e:
        print(f"Failed to parse questions: {e}")
        sys.exit(1)

    # Assertions on Parsing
    assert len(parsed_questions) == 4, f"Expected 4 parsed questions, got {len(parsed_questions)}"
    
    # Q1: definition, comparison, example
    q1 = parsed_questions[0]
    assert any(intent in q1.get("sub_intents", []) for intent in ["definition", "comparison", "example"]), "Q1 sub-intents verification failed"
    
    # Q2: SQL, explanation
    q2 = parsed_questions[1]
    assert any(intent in q2.get("sub_intents", []) for intent in ["SQL", "explanation"]), "Q2 sub-intents verification failed"

    # Q3: ER_mapping, steps, advantages
    q3 = parsed_questions[2]
    assert any(intent in q3.get("sub_intents", []) for intent in ["steps", "advantages", "ER_mapping"]), "Q3 sub-intents verification failed"

    # Q4: diagram, explanation
    q4 = parsed_questions[3]
    assert "diagram" in q4.get("sub_intents", []), "Q4 sub-intents verification failed"

    print("\n--- Solving Questions ---")
    original_models = settings.ANSWER_PACK_MODELS
    settings.ANSWER_PACK_MODELS = ["gemini-3.5-flash", "gemini-3.1-flash-lite"]
    try:
        solved_pack = generate_solved_answers(study_text, parsed_questions)
        solved_questions = solved_pack.get("questions", [])
        print(f"Solved {len(solved_questions)} questions.")
    except Exception as e:
        print(f"Failed to solve questions: {e}")
        sys.exit(1)
    finally:
        settings.ANSWER_PACK_MODELS = original_models

    # Assertions on Solved Answers
    errors = []
    for idx, sq in enumerate(solved_questions, 1):
        q_num = sq.get("question_number")
        answer = sq.get("answer", "")
        dominant = sq.get("dominant_intent")
        sub_intents = sq.get("sub_intents", [])
        word_count = count_words(answer)
        
        print(f"\n--- Solved Question {idx}: {q_num} ({dominant}) ---")
        print(f"Sub-Intents: {sub_intents}")
        print(f"Word Count: {word_count}")
        print(f"Answer Sample:\n{answer[:300]}...\n")
        
        # Word counts checking (10 Marks: 450-800, 5 Marks: 200-350)
        marks = sq.get("marks_category", "")
        if "10" in marks:
            if word_count < 400 or word_count > 850:
                errors.append(f"{q_num} (10 Marks) word count is {word_count} (expected 450-800)")
        elif "5" in marks:
            if word_count < 180 or word_count > 380:
                errors.append(f"{q_num} (5 Marks) word count is {word_count} (expected 200-350)")
                
        # Sub-intent specific validation
        if "comparison" in sub_intents:
            if "|" not in answer:
                errors.append(f"{q_num} with comparison sub-intent missing markdown table")
                
        if "SQL" in sub_intents or dominant == "sql":
            # Check that SQL query block comes first/near start of answer (ignoring whitespace)
            clean_ans = answer.strip()
            if not clean_ans.startswith("```sql"):
                errors.append(f"{q_num} with SQL dominant/sub-intent should start with SQL code block (got: {clean_ans[:50]}...)")
                
        if "diagram" in sub_intents:
            # Check that diagram has no ugly ASCII graphics like +-----+ or |  |
            if "+--" in answer or "|--" in answer or "┌──" in answer:
                errors.append(f"{q_num} with diagram sub-intent seems to contain ASCII art drawings")
                     
        if "extended beyond uploaded notes" in answer.lower():
            errors.append(f"{q_num} contains forbidden grounding disclaimer")

    if errors:
        print("\n=== SUB-INTENT DECOMPOSITION TESTS FAILED ===")
        for err in errors:
            print(f"- {err}")
        sys.exit(1)
    else:
        print("\n=== ALL SUB-INTENT DECOMPOSITION TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    run_sub_intent_tests()
