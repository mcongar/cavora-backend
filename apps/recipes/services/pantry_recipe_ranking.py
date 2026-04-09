"""
Rank recipes by how well they match the user's pantry and expiry urgency.

No AI: deterministic rules only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from django.utils import timezone

from apps.pantry.choices import ProductStatus
from apps.pantry.models import UserProduct
from apps.recipes.models import (
    CategoryIngredientDefault,
    ProductCatalogIngredient,
    Recipe,
    RecipeIngredient,
)

if TYPE_CHECKING:
    pass


@dataclass
class PantryIngredientUrgency:
    """Best (minimum) days-to-expiry for an ingredient across pantry lines."""

    min_days: int | None
    has_unknown_expiry: bool


def _today() -> date:
    return timezone.localdate()


def days_until_expiry(up: UserProduct) -> int | None:
    if not up.expiry_date:
        return None
    return (up.expiry_date - _today()).days


def ingredient_ids_for_user_product(up: UserProduct) -> set[UUID]:
    ids: set[UUID] = set()
    if up.catalog_product_id:
        ids.update(
            ProductCatalogIngredient.objects.filter(
                catalog_product_id=up.catalog_product_id
            ).values_list("ingredient_id", flat=True)
        )
    elif up.manual_category:
        ids.update(
            CategoryIngredientDefault.objects.filter(category=up.manual_category).values_list(
                "ingredient_id", flat=True
            )
        )
    return ids


def build_pantry_urgency_map(user) -> dict[UUID, PantryIngredientUrgency]:
    """
    For each ingredient ID present in the user's active pantry, compute the minimum
    days-to-expiry among lines that contribute that ingredient (only lines with dates).
    """
    out: dict[UUID, PantryIngredientUrgency] = {}
    qs = UserProduct.objects.filter(user=user, status=ProductStatus.ACTIVE, quantity__gt=0)
    for up in qs.select_related("catalog_product"):
        for iid in ingredient_ids_for_user_product(up):
            iid = UUID(str(iid)) if not isinstance(iid, UUID) else iid
            d = days_until_expiry(up)
            if iid not in out:
                out[iid] = PantryIngredientUrgency(min_days=None, has_unknown_expiry=False)
            cur = out[iid]
            if d is None:
                out[iid] = PantryIngredientUrgency(
                    min_days=cur.min_days,
                    has_unknown_expiry=True,
                )
            else:
                new_min = d if cur.min_days is None else min(cur.min_days, d)
                out[iid] = PantryIngredientUrgency(
                    min_days=new_min,
                    has_unknown_expiry=cur.has_unknown_expiry,
                )
    return out


@dataclass
class RecipeScore:
    recipe_id: UUID
    all_required_matched: bool
    urgency_days: int | None
    has_unknown_expiry_in_match: bool
    missing_required_slugs: list[str]
    matched_required_count: int
    required_count: int


def score_recipe(recipe: Recipe, pantry: dict[UUID, PantryIngredientUrgency]) -> RecipeScore:
    required_rows = [ri for ri in recipe.recipe_ingredients.all() if ri.required]
    required_ids = {ri.ingredient_id for ri in required_rows}
    required_count = len(required_ids)

    missing_slugs: list[str] = []
    for ri in required_rows:
        if ri.ingredient_id not in pantry:
            missing_slugs.append(ri.ingredient.slug)

    if required_count == 0:
        all_matched = True
    else:
        all_matched = all(rid in pantry for rid in required_ids)

    urgency_days: int | None = None
    unknown_any = False
    if all_matched and required_ids:
        days_list: list[int] = []
        for rid in required_ids:
            u = pantry[rid]
            if u.min_days is not None:
                days_list.append(u.min_days)
            if u.has_unknown_expiry:
                unknown_any = True
        urgency_days = min(days_list) if days_list else None

    matched_count = len(required_ids & pantry.keys())

    return RecipeScore(
        recipe_id=recipe.id,
        all_required_matched=all_matched,
        urgency_days=urgency_days,
        has_unknown_expiry_in_match=bool(
            unknown_any and urgency_days is None and all_matched and required_ids
        ),
        missing_required_slugs=sorted(set(missing_slugs)),
        matched_required_count=matched_count,
        required_count=required_count,
    )


def sort_key(score: RecipeScore) -> tuple:
    """
    Lower tuple sorts first: complete recipes first, then most urgent (lowest days).
    Missing ingredients last. None urgency sorts after small positive days.
    """
    # Group 0: all matched, group 1: missing
    group = 0 if score.all_required_matched else 1
    # Urgency: lower days = higher priority; None -> treat as large
    u = score.urgency_days
    if u is None:
        urgency_sort = 99999
    else:
        urgency_sort = max(0, u)
    return (group, urgency_sort, str(score.recipe_id))


def rank_recipes_for_user(user, recipe_queryset):
    pantry = build_pantry_urgency_map(user)
    recipes = list(recipe_queryset.prefetch_related("recipe_ingredients__ingredient"))
    scored: list[tuple[Recipe, RecipeScore]] = []
    for r in recipes:
        s = score_recipe(r, pantry)
        scored.append((r, s))
    scored.sort(key=lambda x: sort_key(x[1]))
    return scored, pantry


def recipe_ids_for_user_product_line(user, user_product_id: UUID) -> set[UUID] | None:
    """Return recipe IDs that use at least one ingredient from this pantry line. None if not found."""
    try:
        up = UserProduct.objects.get(user=user, id=user_product_id, status=ProductStatus.ACTIVE)
    except UserProduct.DoesNotExist:
        return None
    ing_ids = ingredient_ids_for_user_product(up)
    if not ing_ids:
        return set()
    return set(
        RecipeIngredient.objects.filter(ingredient_id__in=ing_ids).values_list("recipe_id", flat=True)
    )
