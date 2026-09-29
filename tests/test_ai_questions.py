import pytest

from app.ai.gemini_client import GeminiClient
from app.ai.parsers import parse_and_validate_gemini_json
from app.ai.prompts import build_question_generation_prompt


def test_build_question_generation_prompt():
    prompt = build_question_generation_prompt(
        target_role="Senior Staff Engineer",
        interview_type="TECHNICAL",
        experience_level="SENIOR",
        candidate_skills=["Python", "FastAPI", "PostgreSQL"],
        num_questions=5,
    )
    assert "Senior Staff Engineer" in prompt
    assert "TECHNICAL" in prompt
    assert "Python, FastAPI, PostgreSQL" in prompt


def test_parse_and_validate_gemini_json_clean():
    raw_json = """
    {
      "questions": [
        {
          "question_text": "Explain Python GIL and memory management.",
          "category": "Python",
          "difficulty": "MEDIUM",
          "expected_topics": ["GIL", "Garbage Collection"]
        }
      ]
    }
    """
    questions = parse_and_validate_gemini_json(raw_json)
    assert len(questions) == 1
    assert questions[0].question_text == "Explain Python GIL and memory management."
    assert questions[0].category == "Python"
    assert questions[0].difficulty == "MEDIUM"


def test_parse_and_validate_gemini_json_markdown_fences():
    raw_json = """```json
    {
      "questions": [
        {
          "question_text": "How do you handle Redis rate limiting?",
          "category": "Redis",
          "difficulty": "HARD",
          "expected_topics": ["Sliding Window", "Lua"]
        }
      ]
    }
    ```"""
    questions = parse_and_validate_gemini_json(raw_json)
    assert len(questions) == 1
    assert questions[0].category == "Redis"


def test_parse_and_validate_gemini_json_invalid():
    with pytest.raises(ValueError):
        parse_and_validate_gemini_json("Not a json string")


def test_gemini_fallback_questions():
    client = GeminiClient(api_key=None)
    fallback = client._get_fallback_questions(
        target_role="Backend Developer",
        interview_type="TECHNICAL",
        experience_level="MID",
        num_questions=3,
    )
    assert len(fallback) == 3
    assert fallback[0].question_text is not None
