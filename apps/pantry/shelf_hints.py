"""
Approximate fridge / freezer storage hints (days from reference date).

Not food-safety advice — user-editable in the app.
"""
from __future__ import annotations

from datetime import date, timedelta

from apps.catalog.choices import Category

# Days until suggested "consume by" when stored in fridge (fresh).
FRIDGE_SUGGEST_DAYS: dict[str, int] = {
    Category.DAIRY: 5,
    Category.FRUITS: 5,
    Category.VEGETABLES: 7,
    Category.MEAT: 3,
    Category.FISH: 2,
    Category.BEVERAGES: 14,
    Category.SNACKS: 14,
    Category.CEREALS: 30,
    Category.FROZEN: 7,
    Category.CONDIMENTS: 30,
    Category.BAKERY: 4,
    Category.CANNED: 365,
    Category.OTHER: 7,
}

# Days until suggested "consume by" when stored frozen (from freeze date).
FREEZER_SUGGEST_DAYS: dict[str, int] = {
    Category.DAIRY: 90,
    Category.FRUITS: 365,
    Category.VEGETABLES: 365,
    Category.MEAT: 240,
    Category.FISH: 120,
    Category.BEVERAGES: 180,
    Category.SNACKS: 180,
    Category.CEREALS: 365,
    Category.FROZEN: 365,
    Category.CONDIMENTS: 730,
    Category.BAKERY: 90,
    Category.CANNED: 730,
    Category.OTHER: 180,
}

DEFAULT_FRIDGE = 7
DEFAULT_FREEZER = 180


def effective_category(*, catalog_category: str | None, manual_category: str | None) -> str:
    if catalog_category:
        return catalog_category
    if manual_category:
        return manual_category
    return Category.OTHER


def suggest_days(*, category: str, is_frozen: bool) -> int:
    table = FREEZER_SUGGEST_DAYS if is_frozen else FRIDGE_SUGGEST_DAYS
    return table.get(category, DEFAULT_FREEZER if is_frozen else DEFAULT_FRIDGE)


def suggested_expiry_date(
    *,
    category: str,
    is_frozen: bool,
    reference_date: date,
) -> date:
    """Recommended consume-by date from reference_date (e.g. today or frozen_at)."""
    days = suggest_days(category=category, is_frozen=is_frozen)
    return reference_date + timedelta(days=days)
