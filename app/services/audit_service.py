import logging
from typing import Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

logger = logging.getLogger("app.security")


class AuditService:
    """Service handling persistence of security audit events to database."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def log_event(
        self,
        action: str,
        resource: str,
        user_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """Records security audit log entry in database."""
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource=resource,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db_session.add(entry)
        await self.db_session.commit()
        logger.info(f"Audit Log [{action}]: User='{user_id}' Resource='{resource}' IP='{ip_address}'")
        return entry
