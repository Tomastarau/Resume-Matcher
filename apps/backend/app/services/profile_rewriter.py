"""Master profile rewriting service."""

import json
import logging
from typing import Any

from app.llm import complete_json
from app.prompts.templates import MASTER_PROFILE_REWRITE_PROMPT

logger = logging.getLogger(__name__)


async def rewrite_selected_items(
    subset: dict[str, Any],
    job_description: str,
    fallback_ids: set[int] | None = None,
    profile_skills: list[str] | None = None,
) -> dict[str, Any]:
    """Rewrite selected item descriptions and merge skills for job relevance.

    Skills from technologies fields are guaranteed in code.
    LLM handles ordering and inferring skills from descriptions.
    Falls back to the original subset if the LLM call fails.
    """
    fallback_ids = fallback_ids or set()
    profile_skills = profile_skills or []

    full_items, fallback_items = _split_items_by_fallback(subset, fallback_ids)

    if not full_items and not fallback_items:
        return subset

    guaranteed_skills = _collect_guaranteed_skills(full_items + fallback_items, profile_skills)

    prompt = MASTER_PROFILE_REWRITE_PROMPT.format(
        full_items=json.dumps(full_items, indent=2, ensure_ascii=False),
        fallback_items=json.dumps(fallback_items, indent=2, ensure_ascii=False),
        profile_skills=json.dumps(profile_skills, ensure_ascii=False),
        job_description=job_description,
    )

    try:
        result = await complete_json(
            prompt=prompt,
            system_prompt="You rewrite resume bullet points to highlight job relevance without inventing content.",
            max_tokens=4096,
        )
        return _merge_rewritten(subset, result, profile_skills, guaranteed_skills)
    except Exception as e:
        logger.warning("Profile rewriter failed, using raw subset: %s", e)
        return subset


def _collect_guaranteed_skills(
    items: list[dict[str, Any]],
    profile_skills: list[str],
) -> list[str]:
    """Return profile skills that explicitly appear in any selected item's technologies."""
    profile_skills_casefold = {s.casefold(): s for s in profile_skills}
    seen: set[str] = set()
    guaranteed: list[str] = []

    for item in items:
        for tech in item.get("technologies", []):
            if not isinstance(tech, str):
                continue
            key = tech.strip().casefold()
            if key in profile_skills_casefold and key not in seen:
                seen.add(key)
                guaranteed.append(profile_skills_casefold[key])

    return guaranteed


def _split_items_by_fallback(
    subset: dict[str, Any],
    fallback_ids: set[int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split work experiences and projects into full-emphasis vs fallback lists."""
    full_items: list[dict[str, Any]] = []
    fallback_items: list[dict[str, Any]] = []

    for section_key in ("workExperience", "personalProjects"):
        for item in subset.get(section_key, []):
            item_id = item.get("id")
            entry = {
                "section": section_key,
                "id": item_id,
                "description": item.get("description", []),
                "technologies": item.get("technologies", []),
            }
            if item_id in fallback_ids:
                fallback_items.append(entry)
            else:
                full_items.append(entry)

    return full_items, fallback_items


def _merge_rewritten(
    subset: dict[str, Any],
    result: dict[str, Any],
    profile_skills: list[str],
    guaranteed_skills: list[str],
) -> dict[str, Any]:
    """Merge LLM-rewritten descriptions and skills back into the subset.

    LLM ordering takes priority. Guaranteed skills (from technologies) are
    always included — appended at the end if the LLM dropped them.
    """
    import copy
    merged = copy.deepcopy(subset)

    exp_index = {item["id"]: i for i, item in enumerate(merged.get("workExperience", []))}
    proj_index = {item["id"]: i for i, item in enumerate(merged.get("personalProjects", []))}

    for item in result.get("workExperience", []):
        item_id = item.get("id")
        if item_id in exp_index and isinstance(item.get("description"), list):
            merged["workExperience"][exp_index[item_id]]["description"] = item["description"]

    for item in result.get("projects", []):
        item_id = item.get("id")
        if item_id in proj_index and isinstance(item.get("description"), list):
            merged["personalProjects"][proj_index[item_id]]["description"] = item["description"]

    profile_skills_casefold = {s.casefold(): s for s in profile_skills}
    guaranteed_keys = {s.casefold() for s in guaranteed_skills}

    rewritten_skills = result.get("skills")
    if isinstance(rewritten_skills, list) and rewritten_skills:
        # LLM-ordered skills, filtered to profile only
        llm_skills: list[str] = []
        seen: set[str] = set()
        for s in rewritten_skills:
            if not isinstance(s, str):
                continue
            key = s.strip().casefold()
            if key in profile_skills_casefold and key not in seen:
                seen.add(key)
                llm_skills.append(profile_skills_casefold[key])

        # Append any guaranteed skill the LLM dropped
        for s in guaranteed_skills:
            if s.casefold() not in seen:
                llm_skills.append(s)

        if llm_skills:
            merged.setdefault("additional", {})["technicalSkills"] = llm_skills
    elif guaranteed_skills:
        # LLM returned no skills — fall back to guaranteed only
        merged.setdefault("additional", {})["technicalSkills"] = guaranteed_skills

    return merged
