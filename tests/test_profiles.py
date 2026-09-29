import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.main import app
from app.models.user import UserRole


@pytest.mark.asyncio
async def test_candidate_profile_validation():
    # Test valid CandidateCreate schema validation
    from app.schemas.profile import CandidateCreate

    payload = CandidateCreate(
        full_name="Alice Candidate",
        headline="Backend Engineer",
        experience_years=4.5,
        skills=["Python", "FastAPI", "PostgreSQL"],
        linkedin_url="https://linkedin.com/in/alice",
        github_url="https://github.com/alice",
    )
    assert payload.full_name == "Alice Candidate"
    assert "Python" in payload.skills


@pytest.mark.asyncio
async def test_recruiter_profile_validation():
    from app.schemas.profile import RecruiterCreate

    payload = RecruiterCreate(
        company_name="TechCorp Inc.",
        designation="Senior Technical Recruiter",
        company_website="https://techcorp.example.com",
        department="Engineering",
    )
    assert payload.company_name == "TechCorp Inc."
    assert payload.company_website == "https://techcorp.example.com"
