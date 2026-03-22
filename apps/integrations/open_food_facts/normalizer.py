from .mapper import map_category, get_shelf_life, SUPPORTED_LANGUAGES


def _get_nutri_score(product: dict) -> str:
    raw = product.get("nutriscore_grade", "unknown").lower()
    return raw if raw in ["a", "b", "c", "d", "e"] else "unknown"


def _get_nova_group(product: dict) -> int | None:
    raw = product.get("nova_group")
    try:
        return int(raw) if raw is not None else None
    except (ValueError, TypeError):
        return None


def _get_nutriments(product: dict) -> dict:
    n = product.get("nutriments", {})
    return {
        "calories": n.get("energy-kcal_100g"),
        "proteins": n.get("proteins_100g"),
        "carbs":    n.get("carbohydrates_100g"),
        "fats":     n.get("fat_100g"),
        "sugars":   n.get("sugars_100g"),
    }


def _get_names(product: dict) -> dict:
    """
    Extracts all available product names by language.
    Falls back to generic product_name if language specific is not available.
    """
    generic = product.get("product_name", "").strip()
    print("product", product)
    names = {}
    for lang in SUPPORTED_LANGUAGES:
        name = product.get(f"product_name_{lang}", "").strip()
        print("name", name)
        print("generic", generic)
        names[f"name_{lang}"] = name or generic
    print("names", names)
    return names


def normalize(product: dict, barcode: str = None) -> dict | None:
    """
    Transforms a raw OFF product dict into a flat dict
    ready to create or update a ProductCatalog instance.
    Returns None if the product has no usable name in any language.
    """
    names = _get_names(product)

    # Must have at least one name
    if not any(names.values()):
        return None

    categories = product.get("categories_tags", [])
    category = map_category(categories)

    resolved_barcode = barcode or product.get("code") or None

    return {
        "barcode":         resolved_barcode,
        "off_id":          product.get("id", ""),
        "brands":          product.get("brands", "").strip(),
        "image_url":       product.get("image_front_url", ""),
        "category":        category,
        "nutri_score":     _get_nutri_score(product),
        "nova_group":      _get_nova_group(product),
        "shelf_life_days": get_shelf_life(category),
        **_get_nutriments(product),
        **names,
    }