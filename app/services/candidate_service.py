import math
from typing import Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.models.candidate import Candidate
from app.models.user import User, UserRole
from app.repositories.candidate_repository import ICandidateRepository, SQLAlchemyCandidateRepository
from app.schemas.common import PaginatedResponse
from app.schemas.profile import CandidateCreate, CandidateResponse, CandidateUpdate


class CandidateService:
    """Service encapsulating candidate profile management business logic."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.candidate_repo: ICandidateRepository = SQLAlchemyCandidateRepository(db_session)

    async def create_profile(self, user: User, payload: CandidateCreate) -> CandidateResponse:
        if user.role != UserRole.CANDIDATE:
            raise ForbiddenException(message="Only users registered with the CANDIDATE role can create a candidate profile")

        existing = await self.candidate_repo.get_by_user_id(user.id)
        if existing:
            raise ConflictException(message="A candidate profile already exists for this user account")

        candidate = Candidate(
            user_id=user.id,
            full_name=payload.full_name,
            headline=payload.headline,
            experience_years=payload.experience_years,
            resume_url=payload.resume_url,
            skills=payload.skills,
            linkedin_url=payload.linkedin_url,
            github_url=payload.github_url,
        )

        created = await self.candidate_repo.create(candidate)
        await self.db_session.commit()
        return CandidateResponse.model_validate(created)

    async def get_profile_by_user_id(self, user_id: uuid.UUID) -> CandidateResponse:
        candidate = await self.candidate_repo.get_by_user_id(user_id)
        if not candidate:
            raise NotFoundException(message="Candidate profile not found for current user")
        return CandidateResponse.model_validate(candidate)

    async def get_profile_by_id(self, candidate_id: uuid.UUID) -> CandidateResponse:
        candidate = await self.candidate_repo.get_by_id(candidate_id)
        if not candidate:
            raise NotFoundException(message=f"Candidate profile with ID '{candidate_id}' not found")
        return CandidateResponse.model_validate(candidate)

    async def update_profile(self, user: User, payload: CandidateUpdate) -> CandidateResponse:
        candidate = await self.candidate_repo.get_by_user_id(user.id)
        if not candidate:
            raise NotFoundException(message="Candidate profile not found. Please create one first.")

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(candidate, field, value)

        updated = await self.candidate_repo.update(candidate)
        await self.db_session.commit()
        return CandidateResponse.model_validate(updated)

    async def search_candidates(
        self,
        skill: Optional[str] = None,
        min_experience: Optional[float] = None,
        max_experience: Optional[float] = None,
        page: int = 1,
        size: int = 20,
    ) -> PaginatedResponse[CandidateResponse]:
        page = max(1, page)
        size = min(max(1, size), 100)
        offset = (page - 1) * size

        candidates, total = await self.candidate_repo.search(
            skill=skill,
            min_experience=min_experience,
            max_experience=max_experience,
            offset=offset,
            limit=size,
        )

        items = [CandidateResponse.model_validate(c) for c in candidates]
        pages = math.ceil(total / size) if size > 0 else 0

        return PaginatedResponse[CandidateResponse](
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )
