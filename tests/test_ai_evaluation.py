import pytest

from app.ai.gemini_client import GeminiClient
from app.ai.parsers import parse_and_validate_evaluation_json
from app.ai.prompts import build_answer_evaluation_prompt


def test_build_answer_evaluation_prompt():
    prompt = build_answer_evaluation_prompt(
        question_text="Explain how Python GIL affects multi-threaded applications.",
        category="Python",
        expected_topics=["GIL", "Threading", "Concurrency"],
        candidate_answer="The GIL limits execution of Python bytecode to a single thread at a time.",
    )
    assert "Explain how Python GIL affects multi-threaded applications." in prompt
    assert "GIL, Threading, Concurrency" in prompt
    assert "The GIL limits execution" in prompt


def test_parse_and_validate_evaluation_json():
    raw_json = """
    {
      "technical_score": 8.5,
      "communication_score": 7.0,
      "relevance_score": 9.0,
      "overall_score": 8.2,
      "strengths": ["Accurate GIL definition"],
      "weaknesses": ["Could mention CPython specifics"],
      "improvement_suggestions": ["Elaborate on I/O vs CPU bound tasks"],
      "feedback_text": "Solid concise technical response."
    }
    """
    eval_obj = parse_and_validate_evaluation_json(raw_json)
    assert eval_obj.technical_score == 8.5
    assert eval_obj.communication_score == 7.0
    assert eval_obj.overall_score == 8.2
    assert "Accurate GIL definition" in eval_obj.strengths


def test_fallback_evaluation_generation():
    client = GeminiClient(api_key=None)
    eval_obj = client._get_fallback_evaluation("AsyncIO allows single-threaded non-blocking I/O execution.")
    assert eval_obj.technical_score >= 0.0 and eval_obj.technical_score <= 10.0
    assert eval_obj.feedback_text is not None
