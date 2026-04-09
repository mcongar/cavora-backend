"""
High-level recipe AI: orchestrates generation + persistence and product checks.
"""

from __future__ import annotations

from uuid import UUID

from apps.pantry.choices import ProductStatus
from apps.pantry.models import UserProduct
from apps.recipes.models import Ingredient, Recipe
from apps.recipes.services.ai_recipe_generator import generate_recipe_payload
from apps.recipes.services.pantry_recipe_ranking import (
    ingredient_ids_for_user_product,
    recipe_ids_for_user_product_line,
)
from apps.recipes.services.recipe_ai_persistence import persist_generated_recipe


def anchors_for_user_product(up: UserProduct) -> list[Ingredient]:
    ids = ingredient_ids_for_user_product(up)
    if not ids:
        return []
    return list(Ingredient.objects.filter(id__in=ids).order_by("slug"))


def should_skip_generation(user, up: UserProduct, *, only_if_empty: bool) -> tuple[bool, list[UUID]]:
    if not only_if_empty:
        return False, []
    ids = recipe_ids_for_user_product_line(user, up.id)
    if ids is None:
        return False, []
    if ids:
        return True, list(ids)
    return False, []


def generate_and_save_for_user_product(
    user,
    user_product_id: UUID,
    *,
    only_if_empty: bool = True,
    language: str = "es",
) -> tuple[bool, Recipe | None, list[UUID]]:
    """
    Returns (skipped, recipe_or_none, existing_recipe_ids_if_skipped).
    skipped=True when only_if_empty and matching recipes already exist.
    Raises UserProduct.DoesNotExist if the line is missing (caller → 404).
    """
    try:
        up = UserProduct.objects.get(user=user, id=user_product_id, status=ProductStatus.ACTIVE)
    except UserProduct.DoesNotExist:
        raise UserProduct.DoesNotExist

    skip, existing_ids = should_skip_generation(user, up, only_if_empty=only_if_empty)
    if skip and existing_ids:
        return True, None, existing_ids

    anchors = anchors_for_user_product(up)
    if not anchors:
        raise ValueError(
            "This product has no ingredient mapping. Link catalog ingredients or set a category with defaults."
        )

    payload = generate_recipe_payload(anchors, theme=None, language=language)
    recipe = persist_generated_recipe(payload, ai_generated=True)
    return False, recipe, []


def generate_batch_recipe(
    *,
    theme: str,
    anchor_slugs: list[str] | None = None,
    language: str = "es",
) -> Recipe:
    """For management commands: optional anchors (existing DB ingredients) + theme."""
    anchors: list[Ingredient] = []
    if anchor_slugs:
        anchors = list(Ingredient.objects.filter(slug__in=anchor_slugs).order_by("slug"))
        found = {i.slug for i in anchors}
        missing = set(anchor_slugs) - found
        if missing:
            raise ValueError(f"Unknown ingredient slugs: {sorted(missing)}")
    payload = generate_recipe_payload(anchors, theme=theme or None, language=language)
    return persist_generated_recipe(payload, ai_generated=True)
