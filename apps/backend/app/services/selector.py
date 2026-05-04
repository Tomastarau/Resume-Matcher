"""Master profile selection service."""

import json
import re
from typing import Any

from pydantic import BaseModel, Field

from app.llm import complete_json
from app.prompts.templates import MASTER_PROFILE_SELECTION_PROMPT
from app.schemas import MasterProfile, ResumeData

MAX_WORK_EXPERIENCE = 2
MAX_PROJECTS = 3

WARNING_NO_RELEVANT_WORK_EXPERIENCE = "tailor.warnings.noRelevantWorkExperience"
WARNING_NO_RELEVANT_PROJECT = "tailor.warnings.noRelevantProject"

_ONGOING_MARKERS = {
    "present", "current", "ongoing",
    "présent", "actualidad", "presente",
    "至今", "現在",
}


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
    job_keywords: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[str]]:
    """Select relevant profile items, rewrite them, and return all stages.

    Returns (selection, raw_subset, rewritten_subset, warnings).
    warnings contains i18n keys resolved by the frontend.
    """
    from app.services.profile_rewriter import rewrite_selected_items

    profile = MasterProfile.model_validate(profile_data)
    prompt = MASTER_PROFILE_SELECTION_PROMPT.format(
        profile_json=json.dumps(profile.model_dump(), indent=2, ensure_ascii=False),
        job_keywords=json.dumps(job_keywords, indent=2, ensure_ascii=False),
        job_description=job_description,
    )
    result = await complete_json(
        prompt=prompt,
        system_prompt="You select the most relevant resume evidence for a job.",
        max_tokens=4096,
    )
    normalized_result = _normalize_selection_result(result)
    selection = MasterProfileSelection.model_validate(normalized_result)

    capped_selection, warnings = _apply_caps_and_fallback(selection.model_dump(), profile.model_dump())
    fallback_ids = _collect_fallback_ids(selection.model_dump(), capped_selection)
    raw_subset = build_resume_subset(profile.model_dump(), capped_selection, fallback_ids=fallback_ids)

    rewritten_subset, rewrite_warnings = await rewrite_selected_items(
        raw_subset,
        job_description,
        fallback_ids=fallback_ids,
        profile_skills=profile.skills,
        job_keywords=job_keywords,
    )
    warnings.extend(rewrite_warnings)

    return capped_selection, raw_subset, rewritten_subset, warnings


def _apply_caps_and_fallback(
    selection: dict[str, Any],
    profile: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Cap selection to limits and inject most-recent fallback if a section is empty."""
    warnings: list[str] = []
    result = dict(selection)

    all_experience = profile.get("workExperience", [])
    if len(all_experience) <= MAX_WORK_EXPERIENCE:
        exp_ids = [item["id"] for item in all_experience]
    else:
        exp_ids = result.get("workExperience", [])[:MAX_WORK_EXPERIENCE]
        if not exp_ids and all_experience:
            most_recent = max(all_experience, key=lambda x: _parse_end_year(x.get("years", "")))
            exp_ids = [most_recent["id"]]
            warnings.append(WARNING_NO_RELEVANT_WORK_EXPERIENCE)
    result["workExperience"] = exp_ids

    project_ids: list[int] = result.get("projects", [])[:MAX_PROJECTS]
    if not project_ids and profile.get("projects"):
        project_ids = [profile["projects"][0]["id"]]
        warnings.append(WARNING_NO_RELEVANT_PROJECT)
    result["projects"] = project_ids

    return result, warnings


def _collect_fallback_ids(
    original_selection: dict[str, Any],
    capped_selection: dict[str, Any],
) -> set[int]:
    """Return IDs injected as fallback — not present in the original LLM selection."""
    original_exp = set(original_selection.get("workExperience", []))
    original_proj = set(original_selection.get("projects", []))
    capped_exp = set(capped_selection.get("workExperience", []))
    capped_proj = set(capped_selection.get("projects", []))
    return (capped_exp - original_exp) | (capped_proj - original_proj)


def _parse_end_year(years: str) -> int:
    """Extract the end year from a years string for sorting purposes.

    Returns the current year for ongoing roles, 0 if unparseable.
    """
    import datetime

    if not isinstance(years, str):
        return 0

    parts = re.split(r"\s*[-–—]\s*", years.strip())
    end_part = parts[-1].strip() if parts else ""

    if end_part.casefold() in _ONGOING_MARKERS:
        return datetime.date.today().year

    match = re.search(r"\d{4}", end_part)
    if match:
        return int(match.group())

    match = re.search(r"\d{4}", years)
    if match:
        return int(match.group())

    return 0


def _sort_experience_by_end_year(
    items: list[dict[str, Any]],
    master_order: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Sort work experience items by end year descending.

    Ties preserve master-profile (insertion) order.
    """
    master_index = {item["id"]: i for i, item in enumerate(master_order)}
    return sorted(
        items,
        key=lambda x: (-_parse_end_year(x.get("years", "")), master_index.get(x["id"], 0)),
    )


def _order_projects(
    profile_projects: list[dict[str, Any]],
    selected_ids: list[int],
    fallback_ids: set[int],
) -> list[dict[str, Any]]:
    """Return projects in selector relevance order, fallbacks appended at end."""
    project_by_id = {item["id"]: item for item in profile_projects}

    non_fallback = [
        project_by_id[pid]
        for pid in selected_ids
        if pid in project_by_id and pid not in fallback_ids
    ]
    fallback = [
        project_by_id[pid]
        for pid in selected_ids
        if pid in project_by_id and pid in fallback_ids
    ]
    return non_fallback + fallback


def build_resume_subset(
    profile_data: dict[str, Any],
    selection_data: dict[str, Any] | None = None,
    fallback_ids: set[int] | None = None,
) -> dict[str, Any]:
    """Build a ResumeData subset from the master profile."""
    profile = MasterProfile.model_validate(profile_data).model_dump()
    selection = MasterProfileSelection.model_validate(selection_data or {}).model_dump()
    fallback_ids = fallback_ids or set()

    selected_experience_ids = set(selection["workExperience"])
    selected_project_ids_ordered: list[int] = selection["projects"]
    selected_skills = _normalize_string_selection(selection["skills"])
    selected_languages = _normalize_string_selection(selection["languages"])
    selected_certifications = _normalize_string_selection(selection["certifications"])

    if not selection_data:
        selected_experience_ids = {item["id"] for item in profile["workExperience"]}
        selected_project_ids_ordered = [item["id"] for item in profile["projects"]]
        selected_skills = {item.casefold(): item for item in profile["skills"]}
        selected_languages = {item.casefold(): item for item in profile["languages"]}
        selected_certifications = {
            item.casefold(): item for item in profile["certifications"]
        }

    selected_experiences_raw = [
        item for item in profile["workExperience"]
        if item["id"] in selected_experience_ids
    ]
    sorted_experiences = _sort_experience_by_end_year(
        selected_experiences_raw, profile["workExperience"]
    )

    ordered_projects = _order_projects(
        profile["projects"], selected_project_ids_ordered, fallback_ids
    )

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
        "workExperience": [_experience_to_resume_item(item) for item in sorted_experiences],
        "education": profile["education"],
        "personalProjects": [_project_to_resume_item(item) for item in ordered_projects],
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
        "technologies": item.get("technologies", []),
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
        "technologies": item.get("technologies", []),
    }


def _normalize_string_selection(values: list[str]) -> dict[str, str]:
    return {str(v).strip().casefold(): str(v).strip() for v in values if str(v).strip()}


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
