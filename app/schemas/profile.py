from datetime import datetime
from typing import List, Optional
import uuid

from pydantic import Field, HttpUrl, field_validator

from app.schemas.common import BaseSchema


class CandidateCreate(BaseSchema):
    full_name: str = Field(..., min_length=1, max_length=255, description="Full name")
    headline: Optional[str] = Field(default=None, max_length=255, description="Professional headline")
    experience_years: float = Field(default=0.0, ge=0.0, le=50.0, description="Experience in years")
    resume_url: Optional[str] = Field(default=None, description="Resume URL")
    skills: List[str] = Field(default_factory=list, description="Array of skill strings")
    linkedin_url: Optional[str] = Field(default=None, description="LinkedIn profile URL")
    github_url: Optional[str] = Field(default=None, description="GitHub profile URL")

    @field_validator("linkedin_url", "github_url", "resume_url", mode="before")
    @classmethod
    def validate_urls(cls, v: Optional[str]) -> Optional[str]:
        if v and v.strip() != "":
            if not v.startswith("http://") and not v.startswith("https://"):
                raise ValueError("URL must start with http:// or https://")
            return v.strip()
        return None


class CandidateUpdate(BaseSchema):
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    headline: Optional[str] = Field(default=None, max_length=255)
    experience_years: Optional[float] = Field(default=None, ge=0.0, le=50.0)
    resume_url: Optional[str] = Field(default=None)
    skills: Optional[List[str]] = Field(default=None)
    linkedin_url: Optional[str] = Field(default=None)
    github_url: Optional[str] = Field(default=None)

    @field_validator("linkedin_url", "github_url", "resume_url", mode="before")
    @classmethod
    def validate_urls(cls, v: Optional[str]) -> Optional[str]:
        if v and v.strip() != "":
            if not v.startswith("http://") and not v.startswith("https://"):
                raise ValueError("URL must start with http:// or https://")
            return v.strip()
        return None


class CandidateResponse(BaseSchema):
    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    headline: Optional[str] = None
    experience_years: float
    resume_url: Optional[str] = None
    skills: List[str]
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class RecruiterCreate(BaseSchema):
    company_name: str = Field(..., min_length=1, max_length=255, description="Employer name")
    designation: Optional[str] = Field(default=None, max_length=150, description="Role title")
    company_website: Optional[str] = Field(default=None, description="Company website URL")
    department: Optional[str] = Field(default=None, max_length=100, description="Department")

    @field_validator("company_website", mode="before")
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        if v and v.strip() != "":
            if not v.startswith("http://") and not v.startswith("https://"):
                raise ValueError("Website URL must start with http:// or https://")
            return v.strip()
        return None


class RecruiterUpdate(BaseSchema):
    company_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    designation: Optional[str] = Field(default=None, max_length=150)
    company_website: Optional[str] = Field(default=None)
    department: Optional[str] = Field(default=None, max_length=100)

    @field_validator("company_website", mode="before")
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        if v and v.strip() != "":
            if not v.startswith("http://") and not v.startswith("https://"):
                raise ValueError("Website URL must start with http:// or https://")
            return v.strip()
        return None


class RecruiterResponse(BaseSchema):
    id: uuid.UUID
    user_id: uuid.UUID
    company_name: str
    designation: Optional[str] = None
    company_website: Optional[str] = None
    department: Optional[str] = None
    created_at: datetime
    updated_at: datetime
