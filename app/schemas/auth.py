from datetime import datetime
from typing import Optional
import uuid

from pydantic import EmailStr, Field, field_validator

from app.models.user import UserRole
from app.schemas.common import BaseSchema


class UserCreate(BaseSchema):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=100, description="Password (min 8 chars)")
    first_name: str = Field(..., min_length=1, max_length=100, description="First name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name")
    role: UserRole = Field(default=UserRole.CANDIDATE, description="User role (CANDIDATE or RECRUITER)")

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one digit")
        if not any(char.isalpha() for char in v):
            raise ValueError("Password must contain at least one letter")
        return v


class UserLogin(BaseSchema):
    email: EmailStr = Field(..., description="User login email")
    password: str = Field(..., description="User password")


class TokenResponse(BaseSchema):
    access_token: str = Field(..., description="JWT Access Token (15 min TTL)")
    refresh_token: str = Field(..., description="JWT Refresh Token (7 day TTL)")
    token_type: str = Field(default="bearer", description="Token type schema")
    expires_in: int = Field(..., description="Access token expiration in seconds")


class RefreshTokenRequest(BaseSchema):
    refresh_token: str = Field(..., description="Active JWT Refresh Token")


class UserResponse(BaseSchema):
    id: uuid.UUID = Field(..., description="User UUIDv7 primary key")
    email: EmailStr = Field(..., description="User email address")
    role: UserRole = Field(..., description="User system role")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    is_active: bool = Field(..., description="Active status flag")
    is_verified: bool = Field(..., description="Verification flag")
    last_login_at: Optional[datetime] = Field(default=None, description="Last login timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
