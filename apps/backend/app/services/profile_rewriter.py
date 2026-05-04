"""Master profile rewriting service."""

import asyncio
import copy
import json
import logging
from typing import Any

from app.llm import complete_json
from app.prompts.templates import (
    MASTER_PROFILE_REWRITE_ITEM_PROMPT,
    MASTER_PROFILE_SKILLS_ORDER_PROMPT,
    MASTER_PROFILE_SUMMARY_REWRITE_PROMPT,
)

logger = logging.getLogger(__name__)

WARNING_ITEM_REWRITE_FAILED = "tailor.warnings.itemRewriteFailed"
WARNING_SKILLS_REWRITE_FAILED = "tailor.warnings.skillsRewriteFailed"

MAX_SKILLS = 8


async def rewrite_selected_items(
    subset: dict[str, Any],
    job_description: str,
    fallback_ids: set[int] | None = None,
    profile_skills: list[str] | None = None,
    job_keywords: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Rewrite each item description individually in parallel.

    Returns (rewritten_subset, warnings). warnings contains i18n keys.
    Falls back to original description for any item that fails.
    """
    fallback_ids = fallback_ids or set()
    profile_skills = profile_skills or []
    warnings: list[str] = []

    items = _collect_items(subset)
    if not items:
        return subset, warnings

    candidate_skills = _build_skills_candidate_set(items, profile_skills)
    current_summary = subset.get("summary", "")

    tasks: list[Any] = [
        rewrite_single_item(item, job_description, item["id"] in fallback_ids)
        for item in items
    ]

    skills_task_included = bool(candidate_skills)
    if skills_task_included:
        tasks.append(
            order_skills_by_relevance(candidate_skills, job_keywords or {}, job_description)
        )

    tasks.append(
        _rewrite_summary(current_summary, items, job_description)
    )

    results = await asyncio.gather(*tasks, return_exceptions=True)

    item_results = results[: len(items)]
    if skills_task_included:
        skills_result = results[len(items)]
        summary_result = results[len(items) + 1]
    else:
        skills_result = None
        summary_result = results[len(items)]

    merged = copy.deepcopy(subset)
    item_failed = False

    exp_index = {item["id"]: i for i, item in enumerate(merged.get("workExperience", []))}
    proj_index = {item["id"]: i for i, item in enumerate(merged.get("personalProjects", []))}

    for item, result in zip(items, item_results):
        if isinstance(result, Exception) or not isinstance(result, dict):
            logger.warning("Item rewrite failed for id=%s: %s", item.get("id"), result)
            item_failed = True
            continue
        new_desc = result.get("description")
        if not isinstance(new_desc, list):
            item_failed = True
            continue
        section = item.get("section")
        item_id = item.get("id")
        if section == "workExperience" and item_id in exp_index:
            merged["workExperience"][exp_index[item_id]]["description"] = new_desc
        elif section == "personalProjects" and item_id in proj_index:
            merged["personalProjects"][proj_index[item_id]]["description"] = new_desc

    if item_failed:
        warnings.append(WARNING_ITEM_REWRITE_FAILED)

    if candidate_skills:
        if isinstance(skills_result, Exception) or not isinstance(skills_result, list):
            logger.warning("Skills ordering failed: %s", skills_result)
            warnings.append(WARNING_SKILLS_REWRITE_FAILED)
        else:
            merged.setdefault("additional", {})["technicalSkills"] = skills_result

    if isinstance(summary_result, str) and summary_result.strip():
        merged["summary"] = summary_result.strip()

    return merged, warnings


async def rewrite_single_item(
    item: dict[str, Any],
    job_description: str,
    is_fallback: bool = False,
) -> dict[str, Any]:
    """Rewrite bullet points for a single resume item.

    Returns {"id": ..., "section": ..., "description": [...]}.
    Raises on failure so the caller can detect and fall back.
    """
    fallback_note = (
        "\nThis item is not directly relevant to the job — keep the rewrite minimal and factual."
        if is_fallback
        else ""
    )
    item_payload = {
        "id": item.get("id"),
        "title": item.get("title") or item.get("name", ""),
        "company": item.get("company", ""),
        "technologies": item.get("technologies", []),
        "description": item.get("description", []),
    }
    prompt = MASTER_PROFILE_REWRITE_ITEM_PROMPT.format(
        fallback_note=fallback_note,
        item_json=json.dumps(item_payload, indent=2, ensure_ascii=False),
        job_description=job_description,
    )
    result = await complete_json(
        prompt=prompt,
        system_prompt="You rewrite resume bullet points to highlight job relevance without inventing content.",
        max_tokens=1024,
    )
    desc = result.get("description")
    if not isinstance(desc, list):
        raise ValueError(f"Invalid description for item {item.get('id')}: {result}")
    return {"id": item.get("id"), "section": item.get("section"), "description": desc}


async def order_skills_by_relevance(
    candidate_skills: list[str],
    job_keywords: dict[str, Any],
    job_description: str,
) -> list[str]:
    """Order candidate skills by job relevance via LLM, capped at MAX_SKILLS.

    Raises on failure so the caller can fall back.
    """
    prompt = MASTER_PROFILE_SKILLS_ORDER_PROMPT.format(
        job_keywords=json.dumps(job_keywords, indent=2, ensure_ascii=False),
        job_description=job_description,
        skills_json=json.dumps(candidate_skills, ensure_ascii=False),
    )
    result = await complete_json(
        prompt=prompt,
        system_prompt="You select and order resume skills by job relevance.",
        max_tokens=256,
    )
    skills = result.get("skills")
    if not isinstance(skills, list):
        raise ValueError(f"Invalid skills output: {result}")

    candidate_casefold = {s.casefold(): s for s in candidate_skills}
    ordered: list[str] = []
    seen: set[str] = set()
    for s in skills:
        if not isinstance(s, str):
            continue
        key = s.strip().casefold()
        if key in candidate_casefold and key not in seen:
            seen.add(key)
            ordered.append(candidate_casefold[key])

    return ordered[:MAX_SKILLS]


def _collect_items(subset: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten workExperience and personalProjects into a tagged list."""
    items: list[dict[str, Any]] = []
    for section_key in ("workExperience", "personalProjects"):
        for item in subset.get(section_key, []):
            items.append({**item, "section": section_key})
    return items


def _build_skills_candidate_set(
    items: list[dict[str, Any]],
    profile_skills: list[str],
) -> list[str]:
    """Build skill candidates from selected-item technologies, filtered to profile skills."""
    profile_casefold = {s.casefold(): s for s in profile_skills}
    seen: set[str] = set()
    candidates: list[str] = []
    for item in items:
        for tech in item.get("technologies", []):
            if not isinstance(tech, str):
                continue
            key = tech.strip().casefold()
            if key in profile_casefold and key not in seen:
                seen.add(key)
                candidates.append(profile_casefold[key])
    return candidates


async def _rewrite_summary(
    current_summary: str,
    items: list[dict[str, Any]],
    job_description: str,
) -> str:
    """Rewrite the professional summary for job relevance.

    Returns the original on failure — no warning is emitted for summary failures.
    """
    if not current_summary.strip():
        return current_summary

    from app.prompts.templates import MASTER_PROFILE_SUMMARY_REWRITE_PROMPT

    item_context = [
        {"title": i.get("title") or i.get("name", ""), "technologies": i.get("technologies", [])}
        for i in items
    ]
    prompt = MASTER_PROFILE_SUMMARY_REWRITE_PROMPT.format(
        current_summary=current_summary,
        item_context=json.dumps(item_context, indent=2, ensure_ascii=False),
        job_description=job_description,
    )
    try:
        result = await complete_json(
            prompt=prompt,
            system_prompt="You rewrite professional summaries to highlight job relevance.",
            max_tokens=512,
        )
        return result.get("summary", current_summary)
    except Exception as e:
        logger.warning("Summary rewrite failed, using original: %s", e)
        return current_summary
