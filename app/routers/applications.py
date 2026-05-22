from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas, oauth2
from ..database import get_db
from ..models import ApplicationStatus, JobStatus

router = APIRouter(tags=["Applications"])


# ─────────────────────────────────────────
# State machine: valid transitions
# ─────────────────────────────────────────
#
#   applied → shortlisted   (company reviews candidate)
#   applied → rejected      (company rejects directly)
#   shortlisted → accepted  (company makes offer)
#   shortlisted → rejected  (company rejects after shortlist)
#
VALID_TRANSITIONS = {
    ApplicationStatus.applied:     [ApplicationStatus.shortlisted, ApplicationStatus.rejected],
    ApplicationStatus.shortlisted: [ApplicationStatus.accepted,    ApplicationStatus.rejected],
    ApplicationStatus.accepted:    [],   # terminal state
    ApplicationStatus.rejected:    [],   # terminal state
}


def _check_transition(current: ApplicationStatus, new: ApplicationStatus):
    if new not in VALID_TRANSITIONS[current]:
        allowed = [s.value for s in VALID_TRANSITIONS[current]]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Cannot move from '{current.value}' to '{new.value}'. "
                f"Allowed next states: {allowed or ['none — this is a terminal state']}."
            ),
        )


# ─────────────────────────────────────────
# Candidate endpoints
# ─────────────────────────────────────────

@router.post(
    "/jobs/{job_id}/apply",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.ApplicationOut,
    summary="Apply to a job (candidate only)",
)
def apply_to_job(
    job_id: int,
    data: schemas.ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.require_candidate),
):
    """
    A candidate can apply to a job only once.
    The job must be open.
    You must have a candidate profile before applying.
    """
    profile = current_user.candidate_profile
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Create a candidate profile first via POST /candidate/profile.",
        )

    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with id {job_id} not found.",
        )
    if job.status != JobStatus.open:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This job is no longer accepting applications.",
        )

    # prevent duplicate applications
    existing = db.query(models.Application).filter(
        models.Application.job_id       == job_id,
        models.Application.candidate_id == profile.id,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already applied to this job.",
        )

    application = models.Application(
        job_id       = job_id,
        candidate_id = profile.id,
        cover_letter = data.cover_letter,
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.get(
    "/candidate/applications",
    response_model=List[schemas.ApplicationOut],
    summary="View all your applications (candidate only)",
)
def get_my_applications(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.require_candidate),
):
    """Returns all applications submitted by the logged-in candidate."""
    profile = current_user.candidate_profile
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found.",
        )
    return (
        db.query(models.Application)
        .filter(models.Application.candidate_id == profile.id)
        .order_by(models.Application.created_at.desc())
        .all()
    )


@router.delete(
    "/applications/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Withdraw an application (candidate only, only if status is 'applied')",
)
def withdraw_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.require_candidate),
):
    """
    Candidates can only withdraw while status is still **applied**.
    Once shortlisted, accepted, or rejected, withdrawal is not allowed.
    """
    profile = current_user.candidate_profile
    application = db.query(models.Application).filter(
        models.Application.id           == application_id,
        models.Application.candidate_id == profile.id,
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found.",
        )
    if application.status != ApplicationStatus.applied:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot withdraw — application is already '{application.status.value}'.",
        )

    db.delete(application)
    db.commit()


# ─────────────────────────────────────────
# Company endpoints
# ─────────────────────────────────────────

@router.get(
    "/jobs/{job_id}/applications",
    response_model=List[schemas.ApplicationWithCandidateOut],
    summary="View all applications for a job (company owner only)",
)
def get_job_applications(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.require_company),
):
    """Returns all candidates who applied to one of the company's jobs."""
    profile = current_user.company_profile
    job = db.query(models.Job).filter(models.Job.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with id {job_id} not found.",
        )
    if job.company_id != profile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view applications for your own jobs.",
        )

    return (
        db.query(models.Application)
        .filter(models.Application.job_id == job_id)
        .order_by(models.Application.created_at.desc())
        .all()
    )


@router.put(
    "/applications/{application_id}/status",
    response_model=schemas.ApplicationWithCandidateOut,
    summary="Update application status (company only) — follows state machine rules",
)
def update_application_status(
    application_id: int,
    data: schemas.ApplicationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.require_company),
):
    """
    Move an application through the hiring pipeline.

    **State machine:**
    ```
    applied → shortlisted → accepted
           ↘             ↘
            rejected      rejected
    ```
    Invalid transitions (e.g. accepted → applied) are blocked with 422.
    """
    profile     = current_user.company_profile
    application = db.query(models.Application).filter(
        models.Application.id == application_id
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found.",
        )
    # make sure this application belongs to the company's job
    if application.job.company_id != profile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage applications for your own jobs.",
        )

    _check_transition(application.status, data.status)

    application.status     = data.status
    application.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(application)
    return application