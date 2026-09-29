import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


def generate_uuid7() -> uuid.UUID:
    """
    Generates a time-ordered UUIDv7 according to RFC 9562 specs.
    Provides monotonicity and high index performance in PostgreSQL B-Trees.
    """
    timestamp_ms = int(time.time() * 1000)
    # 48 bits for timestamp
    high = (timestamp_ms & 0xFFFFFFFFFFFF) << 16
    # 12 bits for version (0x7)
    high |= 0x7000 | (int(time.time() * 1000000) & 0x0FFF)
    
    # 64 bits for randomness + variant
    random_bytes = uuid.uuid4().bytes
    low = int.from_bytes(random_bytes[8:], byteorder="big")
    # Set variant bits (10xx)
    low = (low & 0x3FFFFFFFFFFFFFFF) | 0x8000000000000000
    
    return uuid.UUID(int=(high << 64) | low)


class UUIDMixin:
    """Mixin for UUIDv7 Primary Key."""

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid7,
        index=True,
        comment="UUIDv7 time-ordered primary key",
    )


class TimestampMixin:
    """Mixin for record audit timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class SoftDeleteMixin:
    """Mixin for compliance and soft deletion."""

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
        index=True,
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class AuditMixin:
    """Mixin for tracking user mutations."""

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )


class BaseModel(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Abstract Base Model combining UUIDv7 PK, Timestamps, and Soft Delete."""

    __abstract__ = True
