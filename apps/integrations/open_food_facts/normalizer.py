from .mapper import SUPPORTED_LANGUAGES, resolve_category_and_shelf_life
from apps.catalog.scoring import calculate_score


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
        "carbs": n.get("carbohydrates_100g"),
        "fats": n.get("fat_100g"),
        "sugars": n.get("sugars_100g"),
    }


def _get_names(product: dict) -> dict:
    generic = product.get("product_name", "").strip()
    names = {}
    for lang in SUPPORTED_LANGUAGES:
        name = product.get(f"product_name_{lang}", "").strip()
        names[f"name_{lang}"] = name or generic
    return names


def _is_organic(product: dict) -> bool:
    labels = product.get("labels_tags", [])
    return any(
        tag in labels for tag in [
            "en:organic",
            "en:eu-organic",
            "en:usda-organic",
            "fr:ab-agriculture-biologique",
        ]
    )


def normalize(product: dict, barcode: str = None) -> dict | None:
    names = _get_names(product)

    if not any(names.values()):
        return None

    categories = product.get("categories_tags", [])
    category, shelf_life_days = resolve_category_and_shelf_life(categories)
    nutri_score = _get_nutri_score(product)
    is_organic = _is_organic(product)
    score = calculate_score(nutri_score, is_organic)

    resolved_barcode = barcode or product.get("code") or None

    return {
        "barcode": resolved_barcode,
        "off_id": product.get("id", ""),
        "brands": product.get("brands", "").strip(),
        "image_url": product.get("image_front_url", ""),
        "category": category,
        "nutri_score": nutri_score,
        "nova_group": _get_nova_group(product),
        "shelf_life_days": shelf_life_days,
        "is_organic": is_organic,
        "score": score,
        **_get_nutriments(product),
        **names,
    }
