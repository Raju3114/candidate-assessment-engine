import pytest

from app.ai.gemini_client import GeminiClient
from app.ai.parsers import parse_and_validate_report_json
from app.models.report import HiringRecommendation
from app.services.report_service import compute_hiring_recommendation


def test_hiring_recommendation_thresholds():
    assert compute_hiring_recommendation(9.2) == HiringRecommendation.STRONG_HIRE
    assert compute_hiring_recommendation(8.5) == HiringRecommendation.STRONG_HIRE
    assert compute_hiring_recommendation(7.8) == HiringRecommendation.HIRE
    assert compute_hiring_recommendation(7.0) == HiringRecommendation.HIRE
    assert compute_hiring_recommendation(6.0) == HiringRecommendation.NEUTRAL
    assert compute_hiring_recommendation(5.5) == HiringRecommendation.NEUTRAL
    assert compute_hiring_recommendation(4.5) == HiringRecommendation.NO_HIRE
    assert compute_hiring_recommendation(4.0) == HiringRecommendation.NO_HIRE
    assert compute_hiring_recommendation(3.2) == HiringRecommendation.STRONG_NO_HIRE


def test_parse_and_validate_report_json():
    raw_json = """
    {
      "strengths": ["Excellent System Design architecture awareness", "Strong FastAPI async skills"],
      "weaknesses": ["Minor gap in complex SQL joins"],
      "executive_summary": "The candidate performed very well across all technical domain areas."
    }
    """
    report_obj = parse_and_validate_report_json(raw_json)
    assert len(report_obj.strengths) == 2
    assert "System Design" in report_obj.strengths[0]
    assert "FastAPI" in report_obj.strengths[1]


def test_fallback_report_generation():
    client = GeminiClient(api_key=None)
    fallback = client._get_fallback_report(
        target_role="Senior Software Engineer",
        overall_score=8.4,
    )
    assert fallback.strengths is not None
    assert "8.4/10.0" in fallback.executive_summary
