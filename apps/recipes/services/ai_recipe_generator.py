"""
Call OpenAI to produce a single recipe as JSON. No DB writes here.
"""

from __future__ import annotations

import json
import re
from typing import Any

import requests
from django.conf import settings
from pydantic import BaseModel, Field, field_validator

from apps.recipes.models import Ingredient


class OpenAINotConfiguredError(Exception):
    """Missing API key or AI disabled."""


class AiRecipeGenerationError(Exception):
    """OpenAI returned an error or invalid payload."""


class IngredientLine(BaseModel):
    slug: str = Field(max_length=80)
    name_es: str = Field(max_length=120)
    name_en: str = Field(default="", max_length=120)
    required: bool = True
    quantity_note: str = Field(default="", max_length=120)

    @field_validator("slug")
    @classmethod
    def slug_chars(cls, v: str) -> str:
        s = v.strip().lower()
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", s):
            raise ValueError("slug must be lowercase ASCII letters, digits, hyphens")
        return s[:80]


class GeneratedRecipePayload(BaseModel):
    title_es: str = Field(max_length=200)
    title_en: str = Field(default="", max_length=200)
    steps_es: str
    steps_en: str = ""
    prep_minutes: int | None = Field(default=None, ge=1, le=600)
    ingredients: list[IngredientLine] = Field(min_length=2, max_length=24)


def _openai_headers() -> dict[str, str]:
    key = (getattr(settings, "OPENAI_API_KEY", None) or "").strip()
    if not key:
        raise OpenAINotConfiguredError("OPENAI_API_KEY is not set.")
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _build_messages(
    anchor_ingredients: list[Ingredient],
    *,
    theme: str | None,
    language: str,
) -> list[dict[str, str]]:
    anchor_lines = []
    required_slugs = []
    for ing in anchor_ingredients:
        required_slugs.append(ing.slug)
        anchor_lines.append(
            f"- slug `{ing.slug}` (ES: {ing.name_es}; EN: {ing.name_en or ing.name_es})"
        )
    anchor_block = "\n".join(anchor_lines) if anchor_lines else "(none — invent sensible ingredients)"

    theme_block = f"\nTheme / focus: {theme}\n" if theme else ""

    system = (
        "You are a practical home-cooking assistant. "
        "Reply with a single JSON object only, no markdown. "
        "The JSON must match the user's schema: title_es, title_en, steps_es, steps_en, "
        "prep_minutes (integer minutes or null), ingredients (array). "
        "Each ingredient: slug, name_es, name_en, required (boolean), quantity_note (short, e.g. '200 ml'). "
        "Slugs: lowercase ASCII, words separated by hyphens, max 80 chars. "
        "Steps should be clear and numbered implicitly by sentences or newlines. "
        "Titles and steps must be in Spanish (title_es, steps_es) and English (title_en, steps_en). "
        "If English copy is missing, duplicate Spanish sensibly in English fields."
    )
    user = (
        f"Language hint for tone: {language}.\n"
        f"{theme_block}"
        "You MUST include every anchor ingredient below as required ingredients with the EXACT same slug string.\n"
        f"Required anchor slugs (subset of ingredients): {required_slugs}\n"
        f"Anchor details:\n{anchor_block}\n"
        "Add a few more common pantry ingredients if needed. "
        "At least 2 ingredients total. "
        "Do not include fields other than those listed in the schema."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _parse_response(data: dict[str, Any]) -> GeneratedRecipePayload:
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise AiRecipeGenerationError("Unexpected OpenAI response shape.") from e
    if isinstance(content, list):
        text = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    else:
        text = str(content)
    text = text.strip()
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as e:
        raise AiRecipeGenerationError("Model did not return valid JSON.") from e
    try:
        return GeneratedRecipePayload.model_validate(raw)
    except Exception as e:
        raise AiRecipeGenerationError(f"Invalid recipe JSON: {e}") from e


def generate_recipe_payload(
    anchor_ingredients: list[Ingredient],
    *,
    theme: str | None = None,
    language: str = "es",
) -> GeneratedRecipePayload:
    """
    Call OpenAI and return a validated payload. Anchor ingredients must appear with the same slugs.
    """
    if not getattr(settings, "RECIPE_AI_ENABLED", True):
        raise OpenAINotConfiguredError("Recipe AI is disabled (RECIPE_AI_ENABLED=false).")

    model = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")
    messages = _build_messages(anchor_ingredients, theme=theme, language=language)
    body = {
        "model": model,
        "response_format": {"type": "json_object"},
        "messages": messages,
        "temperature": 0.7,
    }
    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=_openai_headers(),
            json=body,
            timeout=90,
        )
    except requests.RequestException as e:
        raise AiRecipeGenerationError(f"OpenAI request failed: {e}") from e

    if r.status_code >= 400:
        raise AiRecipeGenerationError(f"OpenAI HTTP {r.status_code}: {r.text[:500]}")

    payload = _parse_response(r.json())

    required_slugs = {a.slug for a in anchor_ingredients}
    got = {i.slug for i in payload.ingredients}
    missing = required_slugs - got
    if missing:
        raise AiRecipeGenerationError(f"Model omitted anchor slugs: {sorted(missing)}")

    return payload
