from django.db import models


class Category(models.TextChoices):
    DAIRY = "dairy", "Dairy"
    FRUITS = "fruits", "Fruits"
    VEGETABLES = "vegetables", "Vegetables"
    MEAT = "meat", "Meat"
    FISH = "fish", "Fish"
    BEVERAGES = "beverages", "Beverages"
    SNACKS = "snacks", "Snacks"
    CEREALS = "cereals", "Cereals"
    FROZEN = "frozen", "Frozen"
    CONDIMENTS = "condiments", "Condiments"
    BAKERY = "bakery", "Bakery"
    CANNED = "canned", "Canned"
    OTHER = "other", "Other"


class NutriScore(models.TextChoices):
    A = "a", "A"
    B = "b", "B"
    C = "c", "C"
    D = "d", "D"
    E = "e", "E"
    UNKNOWN = "unknown", "Unknown"


class MatchSource(models.TextChoices):
    AI = "ai", "AI"
    USER = "user", "User"
    BARCODE = "barcode", "Barcode"
