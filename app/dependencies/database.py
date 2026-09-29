from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection provider for AsyncSession."""
    async for session in get_db_session():
        yield session
