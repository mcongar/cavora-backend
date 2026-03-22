import requests
from .mapper import SUPPORTED_LANGUAGES

BASE_URL = "https://world.openfoodfacts.org"
TIMEOUT  = 10
USER_AGENT = "Cavora/1.0"

# Request all language names in one call
_NAME_FIELDS = [f"product_name_{lang}" for lang in SUPPORTED_LANGUAGES]

PRODUCT_FIELDS = ",".join([
    "id",
    "code",
    "product_name",
    "brands",
    "categories_tags",
    "nutriscore_grade",
    "nova_group",
    "nutriments",
    "image_front_url",
    *_NAME_FIELDS,
])

SEARCH_FIELDS = ",".join([
    "id",
    "code",
    "product_name",
    "brands",
    "categories_tags",
    "nutriscore_grade",
    "nova_group",
    "nutriments",
    "image_front_url",
    *_NAME_FIELDS,
])


def _get(url: str, params: dict = None) -> dict | None:
    try:
        response = requests.get(
            url,
            params=params,
            timeout=TIMEOUT,
            headers={"User-Agent": USER_AGENT}
        )
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def fetch_by_barcode(barcode: str) -> dict | None:
    url = f"{BASE_URL}/api/v2/product/{barcode}"
    params = {"fields": PRODUCT_FIELDS}
    data = _get(url, params)
    if not data or data.get("status") != 1:
        return None
    return data.get("product")


def search_by_name(query: str, lang: str = "es", page_size: int = 5) -> list:
    url = f"{BASE_URL}/cgi/search.pl"
    params = {
        "search_terms": query,
        "search_simple": 1,
        "action":        "process",
        "json":          1,
        "page_size":     page_size,
        "lc":            lang,
        "fields":        SEARCH_FIELDS,
    }
    data = _get(url, params)
    if not data:
        return []
    return data.get("products", [])