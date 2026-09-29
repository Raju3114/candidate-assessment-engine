import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.models.recruiter import Recruiter
from app.models.user import User, UserRole
from app.repositories.recruiter_repository import IRecruiterRepository, SQLAlchemyRecruiterRepository
from app.schemas.profile import RecruiterCreate, RecruiterResponse, RecruiterUpdate


class RecruiterService:
    """Service encapsulating recruiter profile management business logic."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.recruiter_repo: IRecruiterRepository = SQLAlchemyRecruiterRepository(db_session)

    async def create_profile(self, user: User, payload: RecruiterCreate) -> RecruiterResponse:
        if user.role != UserRole.RECRUITER:
            raise ForbiddenException(message="Only users registered with the RECRUITER role can create a recruiter profile")

        existing = await self.recruiter_repo.get_by_user_id(user.id)
        if existing:
            raise ConflictException(message="A recruiter profile already exists for this user account")

        recruiter = Recruiter(
            user_id=user.id,
            company_name=payload.company_name,
            designation=payload.designation,
            company_website=payload.company_website,
            department=payload.department,
        )

        created = await self.recruiter_repo.create(recruiter)
        await self.db_session.commit()
        return RecruiterResponse.model_validate(created)

    async def get_profile_by_user_id(self, user_id: uuid.UUID) -> RecruiterResponse:
        recruiter = await self.recruiter_repo.get_by_user_id(user_id)
        if not recruiter:
            raise NotFoundException(message="Recruiter profile not found for current user")
        return RecruiterResponse.model_validate(recruiter)

    async def get_profile_by_id(self, recruiter_id: uuid.UUID) -> RecruiterResponse:
        recruiter = await self.recruiter_repo.get_by_id(recruiter_id)
        if not recruiter:
            raise NotFoundException(message=f"Recruiter profile with ID '{recruiter_id}' not found")
        return RecruiterResponse.model_validate(recruiter)

    async def update_profile(self, user: User, payload: RecruiterUpdate) -> RecruiterResponse:
        recruiter = await self.recruiter_repo.get_by_user_id(user.id)
        if not recruiter:
            raise NotFoundException(message="Recruiter profile not found. Please create one first.")

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(recruiter, field, value)

        updated = await self.recruiter_repo.update(recruiter)
        await self.db_session.commit()
        return RecruiterResponse.model_validate(updated)
