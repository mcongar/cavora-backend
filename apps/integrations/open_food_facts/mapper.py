from apps.catalog.choices import Category

CATEGORY_MAP = {
    "en:dairy": Category.DAIRY,
    "en:milks": Category.DAIRY,
    "en:yogurts": Category.DAIRY,
    "en:cheeses": Category.DAIRY,
    "en:fruits": Category.FRUITS,
    "en:fresh-fruits": Category.FRUITS,
    "en:vegetables": Category.VEGETABLES,
    "en:fresh-vegetables": Category.VEGETABLES,
    "en:meats": Category.MEAT,
    "en:poultry": Category.MEAT,
    "en:fish": Category.FISH,
    "en:seafood": Category.FISH,
    "en:beverages": Category.BEVERAGES,
    "en:sodas": Category.BEVERAGES,
    "en:juices": Category.BEVERAGES,
    "en:snacks": Category.SNACKS,
    "en:sweet-snacks": Category.SNACKS,
    "en:cereals": Category.CEREALS,
    "en:pasta": Category.CEREALS,
    "en:rice": Category.CEREALS,
    "en:breads": Category.BAKERY,
    "en:pastries": Category.BAKERY,
    "en:frozen-foods": Category.FROZEN,
    "en:canned-foods": Category.CANNED,
    "en:sauces": Category.CONDIMENTS,
    "en:condiments": Category.CONDIMENTS,
    "en:spreads": Category.CONDIMENTS,
}

SHELF_LIFE_BY_CATEGORY = {
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

SUPPORTED_LANGUAGES = ["es", "en", "fr", "de", "it", "pt"]
DEFAULT_LANGUAGE = "es"


def map_category(off_categories: list) -> str:
    for cat in off_categories:
        if cat in CATEGORY_MAP:
            return CATEGORY_MAP[cat]
    return Category.OTHER


def get_shelf_life(category: str) -> int:
    return SHELF_LIFE_BY_CATEGORY.get(category, 30)


def normalize_language(lang: str) -> str:
    lang = lang.strip().lower()[:2]
    return lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
