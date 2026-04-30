"""Master profile endpoints."""

import json
import logging
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.database import db
from app.schemas import (
    MasterProfile,
    MasterProfileImportRequest,
    MasterProfileImportResponse,
    MasterProfileResponse,
)
from app.services.master_profile import (
    import_resume_data,
    load_master_profile,
    save_master_profile,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/master-profile", tags=["Master Profile"])


@router.get("", response_model=MasterProfileResponse)
async def get_master_profile() -> MasterProfileResponse:
    """Return the saved master profile."""
    profile = load_master_profile()
    if profile is None:
        raise HTTPException(status_code=404, detail="Master profile not found")

    return MasterProfileResponse(
        request_id=str(uuid4()),
        data=MasterProfile.model_validate(profile),
    )


@router.put("", response_model=MasterProfileResponse)
async def put_master_profile(profile: MasterProfile) -> MasterProfileResponse:
    """Replace the full master profile."""
    saved_profile = save_master_profile(profile.model_dump())
    return MasterProfileResponse(
        request_id=str(uuid4()),
        data=MasterProfile.model_validate(saved_profile),
    )


@router.post("/import", response_model=MasterProfileImportResponse)
async def import_master_profile(
    request: MasterProfileImportRequest,
) -> MasterProfileImportResponse:
    """Import structured resume data into the master profile."""
    resume = db.get_resume(request.resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    resume_data = _extract_resume_data(resume)
    if resume_data is None:
        raise HTTPException(
            status_code=400,
            detail="Resume has no structured data available for import.",
        )

    existing_profile = load_master_profile()
    merged_profile = import_resume_data(existing_profile, resume_data)
    saved_profile = save_master_profile(merged_profile)

    return MasterProfileImportResponse(
        message="Master profile updated successfully.",
        request_id=str(uuid4()),
        data=MasterProfile.model_validate(saved_profile),
    )


def _extract_resume_data(resume: dict) -> dict | None:
    processed_data = resume.get("processed_data")
    if isinstance(processed_data, dict):
        return processed_data

    if resume.get("content_type") == "json":
        try:
            parsed = json.loads(resume.get("content", ""))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            logger.warning("Failed to parse resume JSON during master profile import.")

    return None
