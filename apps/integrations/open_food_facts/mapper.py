"""
Open Food Facts categories_tags → Cavora category + shelf life.

- Selection is by **priority** (highest wins), not order in the OFF list — so
  en:spices beats en:beverages when both appear.
- Optional per-tag shelf overrides (e.g. dry spices ~2 years).
"""
from __future__ import annotations

from dataclasses import dataclass

from apps.catalog.choices import Category

SHELF_LIFE_BY_CATEGORY: dict[str, int] = {
    Category.DAIRY: 7,
    Category.FRUITS: 7,
    Category.VEGETABLES: 7,
    Category.MEAT: 3,
    Category.FISH: 2,
    Category.BEVERAGES: 365,
    Category.SNACKS: 180,
    Category.CEREALS: 365,
    Category.BAKERY: 5,
    Category.FROZEN: 180,
    Category.CANNED: 730,
    Category.CONDIMENTS: 365,
    Category.OTHER: 30,
}


@dataclass(frozen=True)
class OffTagRule:
    """OFF categories_tags slug → internal category, priority, optional shelf override."""

    tag: str
    category: str
    priority: int
    shelf_days: int | None = None  # None → SHELF_LIFE_BY_CATEGORY[category]


def _rules() -> list[OffTagRule]:
    """Single place for all OFF tag rules (priority: higher = preferred when multiple match)."""
    C = Category
    return [
        # --- Spices, herbs, dry aromatics (beat broad “beverages” / plant-based parents) ---
        OffTagRule("en:spices", C.CONDIMENTS, 92, 730),
        OffTagRule("en:herbs-and-spices", C.CONDIMENTS, 91, 730),
        OffTagRule("en:powdered-spices", C.CONDIMENTS, 92, 730),
        OffTagRule("en:salts", C.CONDIMENTS, 90, 1095),
        OffTagRule("en:peppers", C.CONDIMENTS, 88, 730),  # often spice jars
        OffTagRule("en:vinegars", C.CONDIMENTS, 86, 730),
        OffTagRule("en:mustards", C.CONDIMENTS, 85, 365),
        OffTagRule("en:ketchups", C.CONDIMENTS, 84, 365),
        OffTagRule("en:mayonnaises", C.CONDIMENTS, 83, 120),
        OffTagRule("en:honeys", C.CONDIMENTS, 82, 730),
        OffTagRule("en:sugars", C.CONDIMENTS, 80, 1095),
        OffTagRule("en:edible-seeds", C.CONDIMENTS, 78, 365),
        OffTagRule("en:seeds", C.CONDIMENTS, 75, 365),
        OffTagRule("en:teas", C.BEVERAGES, 72, 730),
        OffTagRule("en:herbal-teas", C.BEVERAGES, 72, 730),
        OffTagRule("en:infusions", C.BEVERAGES, 71, 730),
        OffTagRule("en:coffees", C.BEVERAGES, 72, 540),
        OffTagRule("en:instant-coffees", C.BEVERAGES, 71, 730),
        # Condiments / sauces (generic, lower than spices) ---
        OffTagRule("en:condiments", C.CONDIMENTS, 85, None),
        OffTagRule("en:sauces", C.CONDIMENTS, 84, None),
        OffTagRule("en:spreads", C.CONDIMENTS, 80, 120),
        OffTagRule("en:pickles", C.CANNED, 78, None),
        OffTagRule("en:olives", C.CANNED, 77, None),
        OffTagRule("en:canned-vegetables", C.CANNED, 76, None),
        # Dairy, meat, fish, produce ---
        OffTagRule("en:dairy", C.DAIRY, 70, None),
        OffTagRule("en:milks", C.DAIRY, 72, None),
        OffTagRule("en:yogurts", C.DAIRY, 73, None),
        OffTagRule("en:cheeses", C.DAIRY, 73, None),
        OffTagRule("en:fruits", C.FRUITS, 70, None),
        OffTagRule("en:fresh-fruits", C.FRUITS, 72, None),
        OffTagRule("en:vegetables", C.VEGETABLES, 70, None),
        OffTagRule("en:fresh-vegetables", C.VEGETABLES, 72, None),
        OffTagRule("en:meats", C.MEAT, 72, None),
        OffTagRule("en:poultry", C.MEAT, 72, None),
        OffTagRule("en:fish", C.FISH, 72, None),
        OffTagRule("en:seafood", C.FISH, 72, None),
        # Bakery, grains, snacks ---
        OffTagRule("en:breads", C.BAKERY, 68, None),
        OffTagRule("en:pastries", C.BAKERY, 67, None),
        OffTagRule("en:cereals", C.CEREALS, 65, None),
        OffTagRule("en:pasta", C.CEREALS, 66, None),
        OffTagRule("en:rice", C.CEREALS, 65, None),
        OffTagRule("en:snacks", C.SNACKS, 62, None),
        OffTagRule("en:sweet-snacks", C.SNACKS, 63, None),
        OffTagRule("en:dried-fruits", C.SNACKS, 64, 180),
        # Frozen / canned generic ---
        OffTagRule("en:frozen-foods", C.FROZEN, 60, None),
        OffTagRule("en:canned-foods", C.CANNED, 62, None),
        # Beverages (specific before generic) ---
        OffTagRule("en:juices", C.BEVERAGES, 58, None),
        OffTagRule("en:sodas", C.BEVERAGES, 58, None),
        OffTagRule("en:waters", C.BEVERAGES, 56, 730),
        OffTagRule("en:alcoholic-beverages", C.BEVERAGES, 55, None),
        OffTagRule("en:wines", C.BEVERAGES, 54, None),
        OffTagRule("en:beers", C.BEVERAGES, 54, None),
        OffTagRule("en:plant-milks", C.BEVERAGES, 57, 180),
        OffTagRule("en:beverages", C.BEVERAGES, 50, None),
        # Very broad parents — only if nothing more specific matched ---
        OffTagRule("en:plant-based-foods-and-beverages", C.OTHER, 15, 30),
        OffTagRule("en:groceries", C.OTHER, 12, 30),
    ]


def _registry() -> dict[str, OffTagRule]:
    reg: dict[str, OffTagRule] = {}
    for rule in _rules():
        old = reg.get(rule.tag)
        if old is None or rule.priority > old.priority:
            reg[rule.tag] = rule
    return reg


_OFF_TAG_REGISTRY: dict[str, OffTagRule] | None = None


def _get_registry() -> dict[str, OffTagRule]:
    global _OFF_TAG_REGISTRY
    if _OFF_TAG_REGISTRY is None:
        _OFF_TAG_REGISTRY = _registry()
    return _OFF_TAG_REGISTRY


def resolve_category_and_shelf_life(off_categories: list | None) -> tuple[str, int]:
    """
    Pick category + shelf life from OFF categories_tags using **max priority** rule.

    Returns (Category.OTHER, 30) when nothing matches.
    """
    if not off_categories:
        return Category.OTHER, SHELF_LIFE_BY_CATEGORY[Category.OTHER]

    reg = _get_registry()
    best: OffTagRule | None = None
    for tag in off_categories:
        rule = reg.get(tag)
        if rule is None:
            continue
        if best is None or rule.priority > best.priority:
            best = rule

    if best is None:
        return Category.OTHER, SHELF_LIFE_BY_CATEGORY[Category.OTHER]

    shelf = (
        best.shelf_days
        if best.shelf_days is not None
        else SHELF_LIFE_BY_CATEGORY.get(
            best.category, SHELF_LIFE_BY_CATEGORY[Category.OTHER]
        )
    )
    return best.category, int(shelf)


def map_category(off_categories: list) -> str:
    """Backward-compatible: category only (uses priority resolution)."""
    cat, _ = resolve_category_and_shelf_life(off_categories)
    return cat


def get_shelf_life(category: str) -> int:
    """Shelf life from internal category only (no OFF tags)."""
    return SHELF_LIFE_BY_CATEGORY.get(category, SHELF_LIFE_BY_CATEGORY[Category.OTHER])


SUPPORTED_LANGUAGES = ["es", "en", "fr", "de", "it", "pt"]
DEFAULT_LANGUAGE = "es"


def normalize_language(lang: str) -> str:
    lang = lang.strip().lower()[:2]
    return lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
