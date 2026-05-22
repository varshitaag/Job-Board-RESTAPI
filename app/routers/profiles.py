from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas, oauth2
from ..database import get_db

router = APIRouter(tags=["Profiles"])


# ═══════════════════════════════════════════
# COMPANY PROFILE ENDPOINTS
# ═══════════════════════════════════════════

@router.post(
    "/company/profile",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.CompanyProfileOut,
    summary="Create your company profile (company only)",
)
def create_company_profile(
    data: schemas.CompanyProfileCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.require_company),
):
    """
    One-time setup after registering as a company.
    You cannot create more than one profile per account.
    """
    if current_user.company_profile:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Company profile already exists. Use PUT to update it.",
        )

    profile         = models.CompanyProfile(**data.dict())
    profile.user_id = current_user.id

    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get(
    "/company/profile",
    response_model=schemas.CompanyProfileOut,
    summary="Get your own company profile",
)
def get_my_company_profile(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.require_company),
):
    if not current_user.company_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Create one via POST /company/profile.",
        )
    return current_user.company_profile


@router.put(
    "/company/profile",
    response_model=schemas.CompanyProfileOut,
    summary="Update your company profile",
)
def update_company_profile(
    data: schemas.CompanyProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.require_company),
):
    profile = current_user.company_profile
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Create one first.",
        )

    # only update fields that were actually sent (partial update)
    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return profile


@router.get(
    "/company/{company_id}/profile",
    response_model=schemas.CompanyProfileOut,
    summary="Get any company's public profile",
)
def get_company_profile_by_id(
    company_id: int,
    db: Session = Depends(get_db),
):
    """Public endpoint — no authentication required."""
    profile = db.query(models.CompanyProfile).filter(
        models.CompanyProfile.id == company_id
    ).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with id {company_id} not found.",
        )
    return profile


# ═══════════════════════════════════════════
# CANDIDATE PROFILE ENDPOINTS
# ═══════════════════════════════════════════

@router.post(
    "/candidate/profile",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.CandidateProfileOut,
    summary="Create your candidate profile (candidate only)",
)
def create_candidate_profile(
    data: schemas.CandidateProfileCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.require_candidate),
):
    if current_user.candidate_profile:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Candidate profile already exists. Use PUT to update it.",
        )

    profile         = models.CandidateProfile(**data.dict())
    profile.user_id = current_user.id

    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get(
    "/candidate/profile",
    response_model=schemas.CandidateProfileOut,
    summary="Get your own candidate profile",
)
def get_my_candidate_profile(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.require_candidate),
):
    if not current_user.candidate_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Create one via POST /candidate/profile.",
        )
    return current_user.candidate_profile


@router.put(
    "/candidate/profile",
    response_model=schemas.CandidateProfileOut,
    summary="Update your candidate profile",
)
def update_candidate_profile(
    data: schemas.CandidateProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.require_candidate),
):
    profile = current_user.candidate_profile
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Create one first.",
        )

    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return profile