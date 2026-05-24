from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr

from .models import UserRole, JobType, JobStatus, ApplicationStatus


# ─────────────────────────────────────────
# Auth
# ─────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: UserRole                      # "company" or "candidate"


class UserOut(BaseModel):
    id: int
    email: EmailStr
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    id: Optional[int] = None


# ─────────────────────────────────────────
# Company profile
# ─────────────────────────────────────────

class CompanyProfileCreate(BaseModel):
    company_name: str
    description: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    industry: Optional[str] = None


class CompanyProfileUpdate(BaseModel):
    company_name: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    industry: Optional[str] = None


class CompanyProfileOut(BaseModel):
    id: int
    company_name: str
    description: Optional[str]
    website: Optional[str]
    location: Optional[str]
    industry: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
# Candidate profile
# ─────────────────────────────────────────

class CandidateProfileCreate(BaseModel):
    full_name: str
    bio: Optional[str] = None
    skills: Optional[str] = None       # comma-separated e.g. "Python, SQL"
    location: Optional[str] = None


class CandidateProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    skills: Optional[str] = None
    location: Optional[str] = None


class CandidateProfileOut(BaseModel):
    id: int
    full_name: str
    bio: Optional[str]
    skills: Optional[str]
    location: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
# Jobs
# ─────────────────────────────────────────

class JobCreate(BaseModel):
    title: str
    description: str
    location: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    job_type: JobType = JobType.full_time
    positions_available: int = 1


class JobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    job_type: Optional[JobType] = None
    status: Optional[JobStatus] = None
    positions_available: Optional[int] = None


class JobOut(BaseModel):
    id: int
    title: str
    description: str
    location: Optional[str]
    salary_min: Optional[int]
    salary_max: Optional[int]
    job_type: JobType
    status: JobStatus
    positions_available: int
    created_at: datetime
    company: CompanyProfileOut          # nested company info

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
# Applications
# ─────────────────────────────────────────

class ApplicationCreate(BaseModel):
    cover_letter: Optional[str] = None


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus


class ApplicationOut(BaseModel):
    """Used by candidates — shows which job they applied to."""
    id: int
    status: ApplicationStatus
    cover_letter: Optional[str]
    created_at: datetime
    updated_at: datetime
    job: JobOut                         # nested job info

    class Config:
        from_attributes = True


class ApplicationWithCandidateOut(BaseModel):
    """Used by companies — shows who applied to their job."""
    id: int
    status: ApplicationStatus
    cover_letter: Optional[str]
    created_at: datetime
    updated_at: datetime
    candidate: CandidateProfileOut      # nested candidate info

    class Config:
        from_attributes = True