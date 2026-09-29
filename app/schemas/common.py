from datetime import datetime
from typing import Generic, List, Optional, TypeVar
import uuid

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base Pydantic schema with ORM mode enabled for SQLAlchemy 2.0 conversion."""

    model_config = ConfigDict(from_attributes=True)


class IdResponse(BaseSchema):
    id: uuid.UUID = Field(..., description="Unique entity identifier (UUIDv7)")


class HealthCheckResponse(BaseSchema):
    status: str = Field(..., description="Health status string (e.g. 'ok')")
    environment: str = Field(..., description="Active runtime environment")
    database_connected: bool = Field(..., description="PostgreSQL connection state")
    redis_connected: bool = Field(..., description="Redis connection state")
    timestamp: datetime = Field(..., description="Health check timestamp")


class PaginatedResponse(BaseSchema, Generic[T]):
    items: List[T] = Field(..., description="Page items array")
    total: int = Field(..., description="Total aggregate matching items count")
    page: int = Field(..., description="Current 1-indexed page number")
    size: int = Field(..., description="Page size limit")
    pages: int = Field(..., description="Total computed pages count")
