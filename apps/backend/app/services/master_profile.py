"""Master profile storage and merge helpers."""

import json
from pathlib import Path
from typing import Any

from app.config import settings
from app.schemas import MasterProfile, ResumeData


def get_master_profile_path() -> Path:
    """Return the master profile storage path."""
    return settings.data_dir / "master_profile.json"


def create_empty_master_profile() -> dict[str, Any]:
    """Create an empty validated master profile payload."""
    return MasterProfile().model_dump()


def master_profile_exists() -> bool:
    """Return whether the master profile file exists."""
    return get_master_profile_path().exists()


def load_master_profile() -> dict[str, Any] | None:
    """Load the master profile from disk if present."""
    path = get_master_profile_path()
    if not path.exists():
        return None

    payload = json.loads(path.read_text())
    return MasterProfile.model_validate(payload).model_dump()


def save_master_profile(profile_data: dict[str, Any]) -> dict[str, Any]:
    """Validate and persist the full master profile."""
    validated = MasterProfile.model_validate(profile_data).model_dump()
    path = get_master_profile_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(validated, indent=2, ensure_ascii=False))
    return validated


def resume_data_to_master_profile(resume_data: dict[str, Any]) -> dict[str, Any]:
    """Convert a structured resume payload into master profile format."""
    validated = ResumeData.model_validate(resume_data)

    return MasterProfile(
        personalInfo={
            "name": validated.personalInfo.name,
            "title": validated.personalInfo.title,
            "email": validated.personalInfo.email,
            "phone": validated.personalInfo.phone,
            "location": validated.personalInfo.location,
            "website": validated.personalInfo.website,
            "linkedin": validated.personalInfo.linkedin,
            "github": validated.personalInfo.github,
            "summary": validated.summary,
        },
        workExperience=[
            {
                "id": item.id,
                "title": item.title,
                "company": item.company,
                "location": item.location,
                "years": item.years,
                "description": item.description,
                "technologies": [],
            }
            for item in validated.workExperience
        ],
        projects=[
            {
                "id": item.id,
                "name": item.name,
                "role": item.role,
                "years": item.years,
                "github": item.github,
                "website": item.website,
                "description": item.description,
                "technologies": [],
            }
            for item in validated.personalProjects
        ],
        education=[item.model_dump() for item in validated.education],
        skills=validated.additional.technicalSkills,
        languages=validated.additional.languages,
        certifications=validated.additional.certificationsTraining,
    ).model_dump()


def import_resume_data(
    existing_profile: dict[str, Any] | None,
    resume_data: dict[str, Any],
) -> dict[str, Any]:
    """Merge structured resume data into the master profile."""
    imported_profile = MasterProfile.model_validate(
        resume_data_to_master_profile(resume_data)
    ).model_dump()
    current_profile = MasterProfile.model_validate(
        existing_profile or create_empty_master_profile()
    ).model_dump()

    current_profile["personalInfo"] = _merge_personal_info(
        current_profile["personalInfo"],
        imported_profile["personalInfo"],
    )
    current_profile["workExperience"] = _merge_items(
        current_profile["workExperience"],
        imported_profile["workExperience"],
        key_builder=_experience_key,
        field_names=("title", "company", "location", "years"),
    )
    current_profile["projects"] = _merge_items(
        current_profile["projects"],
        imported_profile["projects"],
        key_builder=_project_key,
        field_names=("name", "role", "years", "github", "website"),
    )
    current_profile["education"] = _merge_items(
        current_profile["education"],
        imported_profile["education"],
        key_builder=_education_key,
        field_names=("institution", "degree", "years", "description"),
    )
    current_profile["skills"] = _merge_string_lists(
        current_profile["skills"],
        imported_profile["skills"],
    )
    current_profile["languages"] = _merge_string_lists(
        current_profile["languages"],
        imported_profile["languages"],
    )
    current_profile["certifications"] = _merge_string_lists(
        current_profile["certifications"],
        imported_profile["certifications"],
    )

    return MasterProfile.model_validate(current_profile).model_dump()


def _merge_personal_info(
    existing: dict[str, Any],
    incoming: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(existing)
    for field, value in incoming.items():
        if _has_value(merged.get(field)):
            continue
        if _has_value(value):
            merged[field] = value
    return merged


def _merge_items(
    existing_items: list[dict[str, Any]],
    incoming_items: list[dict[str, Any]],
    *,
    key_builder: Any,
    field_names: tuple[str, ...],
) -> list[dict[str, Any]]:
    merged_items = [dict(item) for item in existing_items]
    next_id = _next_numeric_id(merged_items)

    for incoming in incoming_items:
        incoming_key = key_builder(incoming)
        matched_index = next(
            (
                index
                for index, existing in enumerate(merged_items)
                if key_builder(existing) == incoming_key
            ),
            None,
        )

        if matched_index is None:
            new_item = dict(incoming)
            new_item["id"] = next_id
            next_id += 1
            merged_items.append(new_item)
            continue

        existing_item = dict(merged_items[matched_index])
        for field_name in field_names:
            if not _has_value(existing_item.get(field_name)) and _has_value(
                incoming.get(field_name)
            ):
                existing_item[field_name] = incoming[field_name]

        if "description" in existing_item or "description" in incoming:
            existing_item["description"] = _merge_string_lists(
                existing_item.get("description", []),
                incoming.get("description", []),
            )
        if "technologies" in existing_item or "technologies" in incoming:
            existing_item["technologies"] = _merge_string_lists(
                existing_item.get("technologies", []),
                incoming.get("technologies", []),
            )

        merged_items[matched_index] = existing_item

    return merged_items


def _merge_string_lists(
    existing_values: list[str] | None,
    incoming_values: list[str] | None,
) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()

    for raw_value in (existing_values or []) + (incoming_values or []):
        text = str(raw_value).strip()
        if not text:
            continue
        normalized = text.casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        merged.append(text)

    return merged


def _next_numeric_id(items: list[dict[str, Any]]) -> int:
    numeric_ids = [
        int(item.get("id"))
        for item in items
        if isinstance(item.get("id"), int) and int(item.get("id")) > 0
    ]
    return max(numeric_ids, default=0) + 1


def _normalize_key_part(value: Any) -> str:
    return str(value or "").strip().casefold()


def _experience_key(item: dict[str, Any]) -> tuple[str, str, str]:
    return (
        _normalize_key_part(item.get("title")),
        _normalize_key_part(item.get("company")),
        _normalize_key_part(item.get("years")),
    )


def _project_key(item: dict[str, Any]) -> tuple[str, str]:
    return (
        _normalize_key_part(item.get("name")),
        _normalize_key_part(item.get("years")),
    )


def _education_key(item: dict[str, Any]) -> tuple[str, str, str]:
    return (
        _normalize_key_part(item.get("institution")),
        _normalize_key_part(item.get("degree")),
        _normalize_key_part(item.get("years")),
    )


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(str(entry).strip() for entry in value)
    return True
