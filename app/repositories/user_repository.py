from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class IUserRepository(ABC):
    """Abstract interface repository for User persistence operations."""

    @abstractmethod
    async def create(self, user: User) -> User: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]: ...

    @abstractmethod
    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]: ...

    @abstractmethod
    async def update_last_login(self, user_id: uuid.UUID) -> None: ...

    @abstractmethod
    async def update(self, user: User) -> User: ...


class SQLAlchemyUserRepository(IUserRepository):
    """Concrete SQLAlchemy 2.0 repository for User entities."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(
            User.email == email.lower(),
            User.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        stmt = select(User).where(
            User.id == user_id,
            User.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_last_login(self, user_id: uuid.UUID) -> None:
        user = await self.get_by_id(user_id)
        if user:
            user.last_login_at = datetime.now(timezone.utc)
            await self._session.flush()

    async def update(self, user: User) -> User:
        await self._session.flush()
        await self._session.refresh(user)
        return user
