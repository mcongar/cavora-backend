"""
Persist a GeneratedRecipePayload into Ingredient + Recipe + RecipeIngredient rows.
"""

from __future__ import annotations

from django.db import transaction

from apps.catalog.choices import Category
from apps.recipes.models import Ingredient, Recipe, RecipeIngredient
from apps.recipes.services.ai_recipe_generator import GeneratedRecipePayload


@transaction.atomic
def persist_generated_recipe(payload: GeneratedRecipePayload, *, ai_generated: bool = True) -> Recipe:
    ingredients: dict[str, Ingredient] = {}
    for line in payload.ingredients:
        ing, _ = Ingredient.objects.get_or_create(
            slug=line.slug,
            defaults={
                "name_es": line.name_es[:120],
                "name_en": (line.name_en or "")[:120],
                "category": Category.OTHER,
            },
        )
        ingredients[line.slug] = ing

    recipe = Recipe.objects.create(
        title_es=payload.title_es[:200],
        title_en=(payload.title_en or "")[:200],
        steps_es=payload.steps_es,
        steps_en=payload.steps_en or "",
        prep_minutes=payload.prep_minutes,
        is_published=True,
        ai_generated=ai_generated,
    )
    for line in payload.ingredients:
        RecipeIngredient.objects.create(
            recipe=recipe,
            ingredient=ingredients[line.slug],
            required=line.required,
            quantity_note=(line.quantity_note or "")[:120],
        )
    return recipe
