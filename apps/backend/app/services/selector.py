"""Master profile selection service."""

import json
from typing import Any

from pydantic import BaseModel, Field

from app.llm import complete_json
from app.prompts.templates import MASTER_PROFILE_SELECTION_PROMPT
from app.schemas import MasterProfile, ResumeData


class MasterProfileSelection(BaseModel):
    """Selected master profile items for a job description."""

    workExperience: list[int] = Field(default_factory=list)
    projects: list[int] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)


async def select_master_profile_subset(
    profile_data: dict[str, Any],
    job_description: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Select relevant profile items and return the selection and resume subset."""
    profile = MasterProfile.model_validate(profile_data)
    prompt = MASTER_PROFILE_SELECTION_PROMPT.format(
        profile_json=json.dumps(profile.model_dump(), indent=2, ensure_ascii=False),
        job_description=job_description,
    )
    result = await complete_json(
        prompt=prompt,
        system_prompt="You select the most relevant resume evidence for a job.",
        max_tokens=4096,
    )
    normalized_result = _normalize_selection_result(result)
    selection = MasterProfileSelection.model_validate(normalized_result)
    subset = build_resume_subset(profile.model_dump(), selection.model_dump())
    return selection.model_dump(), subset


def build_resume_subset(
    profile_data: dict[str, Any],
    selection_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a ResumeData subset from the master profile."""
    profile = MasterProfile.model_validate(profile_data).model_dump()
    selection = MasterProfileSelection.model_validate(selection_data or {}).model_dump()

    selected_experience_ids = set(selection["workExperience"])
    selected_project_ids = set(selection["projects"])
    selected_skills = _normalize_string_selection(selection["skills"])
    selected_languages = _normalize_string_selection(selection["languages"])
    selected_certifications = _normalize_string_selection(selection["certifications"])

    if not selection_data:
        selected_experience_ids = {item["id"] for item in profile["workExperience"]}
        selected_project_ids = {item["id"] for item in profile["projects"]}
        selected_skills = {item.casefold(): item for item in profile["skills"]}
        selected_languages = {item.casefold(): item for item in profile["languages"]}
        selected_certifications = {
            item.casefold(): item for item in profile["certifications"]
        }

    resume_data = {
        "personalInfo": {
            "name": profile["personalInfo"]["name"],
            "title": profile["personalInfo"].get("title", ""),
            "email": profile["personalInfo"]["email"],
            "phone": profile["personalInfo"]["phone"],
            "location": profile["personalInfo"]["location"],
            "website": profile["personalInfo"].get("website"),
            "linkedin": profile["personalInfo"].get("linkedin"),
            "github": profile["personalInfo"].get("github"),
        },
        "summary": profile["personalInfo"].get("summary", ""),
        "workExperience": [
            _experience_to_resume_item(item)
            for item in profile["workExperience"]
            if item["id"] in selected_experience_ids
        ],
        "education": profile["education"],
        "personalProjects": [
            _project_to_resume_item(item)
            for item in profile["projects"]
            if item["id"] in selected_project_ids
        ],
        "additional": {
            "technicalSkills": [
                item
                for item in profile["skills"]
                if item.casefold() in selected_skills
            ],
            "languages": [
                item
                for item in profile["languages"]
                if item.casefold() in selected_languages
            ],
            "certificationsTraining": [
                item
                for item in profile["certifications"]
                if item.casefold() in selected_certifications
            ],
            "awards": [],
        },
        "sectionMeta": [],
        "customSections": {},
    }

    return ResumeData.model_validate(resume_data).model_dump()


def build_full_resume_from_profile(profile_data: dict[str, Any]) -> dict[str, Any]:
    """Convert the full master profile into a ResumeData payload."""
    return build_resume_subset(profile_data, None)


def _experience_to_resume_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "title": item.get("title", ""),
        "company": item.get("company", ""),
        "location": item.get("location"),
        "years": item.get("years", ""),
        "description": item.get("description", []),
    }


def _project_to_resume_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "name": item.get("name", ""),
        "role": item.get("role", ""),
        "years": item.get("years", ""),
        "github": item.get("github"),
        "website": item.get("website"),
        "description": item.get("description", []),
    }


def _normalize_string_selection(values: list[str]) -> dict[str, str]:
    return {str(value).strip().casefold(): str(value).strip() for value in values if str(value).strip()}


def _normalize_selection_result(result: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {}

    return {
        "workExperience": _normalize_numeric_selection(result.get("workExperience")),
        "projects": _normalize_numeric_selection(result.get("projects")),
        "skills": _normalize_text_selection(result.get("skills")),
        "languages": _normalize_text_selection(result.get("languages")),
        "certifications": _normalize_text_selection(result.get("certifications")),
    }


def _normalize_numeric_selection(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []

    normalized: list[int] = []
    for item in value:
        candidate = item
        if isinstance(item, dict):
            candidate = item.get("id")
        try:
            normalized.append(int(candidate))
        except (TypeError, ValueError):
            continue
    return normalized


def _normalize_text_selection(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    normalized: list[str] = []
    for item in value:
        candidate = item
        if isinstance(item, dict):
            candidate = (
                item.get("name")
                or item.get("value")
                or item.get("label")
                or item.get("title")
            )
        if candidate is None:
            continue
        text = str(candidate).strip()
        if text:
            normalized.append(text)
    return normalized
