from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import models, schemas, oauth2
from ..database import get_db
from ..models import JobStatus

router = APIRouter(prefix="/jobs", tags=["Jobs"])


# ─────────────────────────────────────────
# Public endpoints (no auth required)
# ─────────────────────────────────────────

@router.get(
    "",
    response_model=List[schemas.JobOut],
    summary="Browse all open jobs with optional filters",
)
def get_jobs(
    db: Session = Depends(get_db),
    search:     Optional[str] = Query(None,  description="Search in title or description"),
    location:   Optional[str] = Query(None,  description="Filter by location"),
    job_type:   Optional[models.JobType] = Query(None, description="full_time | part_time | contract | remote"),
    salary_min: Optional[int] = Query(None,  description="Minimum salary filter"),
    limit:      int           = Query(10,    ge=1, le=100),
    skip:       int           = Query(0,     ge=0),
):
    """
    Public job board. Returns only **open** jobs.
    Supports keyword search, location filter, job type, and salary filter.
    """
    query = (
        db.query(models.Job)
        .join(models.CompanyProfile)
        .filter(models.Job.status == JobStatus.open)
    )

    if search:
        query = query.filter(
            models.Job.title.ilike(f"%{search}%")
            | models.Job.description.ilike(f"%{search}%")
        )
    if location:
        query = query.filter(models.Job.location.ilike(f"%{location}%"))
    if job_type:
        query = query.filter(models.Job.job_type == job_type)
    if salary_min is not None:
        query = query.filter(models.Job.salary_min >= salary_min)

    return query.order_by(models.Job.created_at.desc()).offset(skip).limit(limit).all()


@router.get(
    "/{job_id}",
    response_model=schemas.JobOut,
    summary="Get a single job by ID",
)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with id {job_id} not found.",
        )
    return job


# ─────────────────────────────────────────
# Company-only endpoints
# ─────────────────────────────────────────

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.JobOut,
    summary="Post a new job (company only)",
)
def create_job(
    data: schemas.JobCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.require_company),
):
    """Company must have a profile before posting a job."""
    profile = current_user.company_profile
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Create a company profile first via POST /company/profile.",
        )

    job            = models.Job(**data.dict())
    job.company_id = profile.id

    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get(
    "/company/mine",
    response_model=List[schemas.JobOut],
    summary="Get all jobs posted by your company",
)
def get_my_jobs(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.require_company),
):
    profile = current_user.company_profile
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company profile not found.",
        )
    return (
        db.query(models.Job)
        .filter(models.Job.company_id == profile.id)
        .order_by(models.Job.created_at.desc())
        .all()
    )


@router.put(
    "/{job_id}",
    response_model=schemas.JobOut,
    summary="Update a job posting (company owner only)",
)
def update_job(
    job_id: int,
    data: schemas.JobUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.require_company),
):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with id {job_id} not found.",
        )
    if job.company_id != current_user.company_profile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own job postings.",
        )

    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(job, key, value)

    db.commit()
    db.refresh(job)
    return job


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a job posting (company owner only)",
)
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.require_company),
):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with id {job_id} not found.",
        )
    if job.company_id != current_user.company_profile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own job postings.",
        )

    db.delete(job)
    db.commit()