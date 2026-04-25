"""
Approximate storage hints (days from reference date): pantry, fridge, or freezer.

Not food-safety advice — user-editable in the app.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING, Literal

from apps.catalog.choices import Category

if TYPE_CHECKING:
    pass

StorageKey = Literal["pantry", "fridge", "freezer"]

# Room-temperature / dry storage (despensa).
PANTRY_SUGGEST_DAYS: dict[str, int] = {
    Category.DAIRY: 5,
    Category.FRUITS: 7,
    Category.VEGETABLES: 7,
    Category.MEAT: 2,
    Category.FISH: 1,
    Category.BEVERAGES: 120,
    Category.SNACKS: 60,
    Category.CEREALS: 120,
    Category.FROZEN: 7,
    Category.CONDIMENTS: 180,
    Category.BAKERY: 5,
    Category.CANNED: 730,
    Category.OTHER: 30,
}

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

DEFAULT_PANTRY = 30
DEFAULT_FRIDGE = 7
DEFAULT_FREEZER = 180

_TABLES: dict[StorageKey, tuple[dict[str, int], int]] = {
    "pantry": (PANTRY_SUGGEST_DAYS, DEFAULT_PANTRY),
    "fridge": (FRIDGE_SUGGEST_DAYS, DEFAULT_FRIDGE),
    "freezer": (FREEZER_SUGGEST_DAYS, DEFAULT_FREEZER),
}


def effective_category(*, catalog_category: str | None, manual_category: str | None) -> str:
    if catalog_category:
        return catalog_category
    if manual_category:
        return manual_category
    return Category.OTHER


def suggest_days(
    *,
    category: str,
    storage: StorageKey | None = None,
    is_frozen: bool | None = None,
) -> int:
    """
    Suggested days until consume-by. Prefer `storage`; if omitted, `is_frozen`
    maps to fridge (False) or freezer (True) for backward compatibility.
    """
    if storage is not None:
        key: StorageKey = storage
    elif is_frozen is not None:
        key = "freezer" if is_frozen else "fridge"
    else:
        key = "fridge"
    table, default = _TABLES[key]
    return table.get(category, default)


def suggested_expiry_date(
    *,
    category: str,
    reference_date: date,
    storage: StorageKey | None = None,
    is_frozen: bool | None = None,
) -> date:
    """Recommended consume-by date from reference_date (e.g. today or frozen_at)."""
    days = suggest_days(category=category, storage=storage, is_frozen=is_frozen)
    return reference_date + timedelta(days=days)
