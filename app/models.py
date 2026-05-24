import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Boolean, Text,
    TIMESTAMP, ForeignKey, Enum as SAEnum, text
)
from sqlalchemy.orm import relationship

from .database import Base


# ─────────────────────────────────────────
# Enums  (stored as strings in the DB)
# ─────────────────────────────────────────

class UserRole(str, enum.Enum):
    company   = "company"
    candidate = "candidate"


class JobType(str, enum.Enum):
    full_time = "full_time"
    part_time = "part_time"
    contract  = "contract"
    remote    = "remote"


class JobStatus(str, enum.Enum):
    open   = "open"
    closed = "closed"


class ApplicationStatus(str, enum.Enum):
    applied     = "applied"      # candidate just submitted
    shortlisted = "shortlisted"  # company moved forward
    accepted    = "accepted"     # company hired
    rejected    = "rejected"     # company rejected


# ─────────────────────────────────────────
# Tables
# ─────────────────────────────────────────

class User(Base):
    """
    Base auth table. Role determines what the user can do.
    company   → can create jobs, review applications
    candidate → can apply to jobs, track their applications
    """
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, nullable=False)
    email      = Column(String, nullable=False, unique=True)
    password   = Column(String, nullable=False)          # hashed password
    role       = Column(SAEnum(UserRole), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False,
                        server_default=text("now()"))

    # one-to-one relationships — only one of these will exist per user
    company_profile   = relationship("CompanyProfile",
                                     back_populates="user", uselist=False)
    candidate_profile = relationship("CandidateProfile",
                                     back_populates="user", uselist=False)


class CompanyProfile(Base):
    """
    Extra info for company users.
    Created separately after registration via POST /company/profile.
    """
    __tablename__ = "company_profiles"

    id           = Column(Integer, primary_key=True, nullable=False)
    user_id      = Column(Integer,
                          ForeignKey("users.id", ondelete="CASCADE"),
                          unique=True, nullable=False)
    company_name = Column(String, nullable=False)
    description  = Column(Text, nullable=True)
    website      = Column(String, nullable=True)
    location     = Column(String, nullable=True)
    industry     = Column(String, nullable=True)
    created_at   = Column(TIMESTAMP(timezone=True), nullable=False,
                          server_default=text("now()"))

    user = relationship("User", back_populates="company_profile")
    jobs = relationship("Job", back_populates="company",
                        cascade="all, delete")


class CandidateProfile(Base):
    """
    Extra info for candidate users.
    Created separately after registration via POST /candidate/profile.
    """
    __tablename__ = "candidate_profiles"

    id         = Column(Integer, primary_key=True, nullable=False)
    user_id    = Column(Integer,
                        ForeignKey("users.id", ondelete="CASCADE"),
                        unique=True, nullable=False)
    full_name  = Column(String, nullable=False)
    bio        = Column(Text, nullable=True)
    skills     = Column(String, nullable=True)   # e.g. "Python, FastAPI, SQL"
    location   = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False,
                        server_default=text("now()"))

    user         = relationship("User", back_populates="candidate_profile")
    applications = relationship("Application", back_populates="candidate",
                                cascade="all, delete")


class Job(Base):
    """
    A job posting owned by a company.
    Only the owning company can edit or close it.
    """
    __tablename__ = "jobs"

    id                  = Column(Integer, primary_key=True, nullable=False)
    company_id          = Column(Integer,
                                 ForeignKey("company_profiles.id", ondelete="CASCADE"),
                                 nullable=False)
    title               = Column(String, nullable=False)
    description         = Column(Text, nullable=False)
    location            = Column(String, nullable=True)
    salary_min          = Column(Integer, nullable=True)
    salary_max          = Column(Integer, nullable=True)
    job_type            = Column(SAEnum(JobType), nullable=False,
                                 default=JobType.full_time)
    status              = Column(SAEnum(JobStatus), nullable=False,
                                 server_default="open")
    positions_available = Column(Integer, nullable=False, default=1)
    created_at          = Column(TIMESTAMP(timezone=True), nullable=False,
                                 server_default=text("now()"))

    company      = relationship("CompanyProfile", back_populates="jobs")
    applications = relationship("Application", back_populates="job",
                                cascade="all, delete")


class Application(Base):
    """
    A candidate's application to a job.
    Composite uniqueness: one candidate can apply to a job only once.
    Status follows a one-way state machine:
        applied → shortlisted → accepted
                             → rejected
        applied → rejected
    """
    __tablename__ = "applications"

    id           = Column(Integer, primary_key=True, nullable=False)
    job_id       = Column(Integer,
                          ForeignKey("jobs.id", ondelete="CASCADE"),
                          nullable=False)
    candidate_id = Column(Integer,
                          ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
                          nullable=False)
    status       = Column(SAEnum(ApplicationStatus), nullable=False,
                          server_default="applied")
    cover_letter = Column(Text, nullable=True)
    created_at   = Column(TIMESTAMP(timezone=True), nullable=False,
                          server_default=text("now()"))
    updated_at   = Column(TIMESTAMP(timezone=True), nullable=False,
                          server_default=text("now()"))

    job       = relationship("Job", back_populates="applications")
    candidate = relationship("CandidateProfile", back_populates="applications")