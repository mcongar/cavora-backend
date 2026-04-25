"""Heuristic default storage (pantry vs fridge) from catalog category for legacy rows and API defaults."""

from __future__ import annotations

from apps.catalog.choices import Category
from .choices import Storage

# "Dry" / long shelf at room temperature (aligned with app pantry heuristic).
DRY_CATEGORIES: frozenset[str] = frozenset(
    {
        Category.CEREALS,
        Category.CANNED,
        Category.SNACKS,
        Category.CONDIMENTS,
        Category.BEVERAGES,
        Category.BAKERY,
    }
)


def default_storage_for_category(category: str) -> str:
    if category in DRY_CATEGORIES:
        return Storage.PANTRY
    return Storage.FRIDGE
