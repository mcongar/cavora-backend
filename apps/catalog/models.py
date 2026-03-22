from django.db import models
from common.models import BaseModel
from .choices import Category, NutriScore, MatchSource


class ProductCatalog(BaseModel):
    # Identification
    barcode = models.CharField(max_length=64, unique=True, null=True, blank=True)
    off_id  = models.CharField(max_length=100, unique=True, blank=True)

    # Names by language — fallback chain: requested → es → en → ""
    name_es = models.CharField(max_length=255, blank=True)
    name_en = models.CharField(max_length=255, blank=True)
    name_fr = models.CharField(max_length=255, blank=True)
    name_de = models.CharField(max_length=255, blank=True)
    name_it = models.CharField(max_length=255, blank=True)
    name_pt = models.CharField(max_length=255, blank=True)

    # Brands
    brands = models.CharField(max_length=255, blank=True)

    # Image
    image_url = models.URLField(blank=True)

    # Universal data — language independent
    category        = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    nutri_score     = models.CharField(max_length=10, choices=NutriScore.choices, default=NutriScore.UNKNOWN)
    nova_group      = models.PositiveSmallIntegerField(null=True, blank=True)
    calories        = models.FloatField(null=True, blank=True)
    proteins        = models.FloatField(null=True, blank=True)
    carbs           = models.FloatField(null=True, blank=True)
    fats            = models.FloatField(null=True, blank=True)
    sugars          = models.FloatField(null=True, blank=True)
    shelf_life_days = models.PositiveIntegerField(null=True, blank=True)
    last_synced_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "product_catalog"
        indexes = [
            models.Index(fields=["barcode"]),
            models.Index(fields=["off_id"]),
        ]

    def get_name(self, lang: str = "es") -> str:
        return (
            getattr(self, f"name_{lang}", "")
            or self.name_es
            or self.name_en
            or ""
        )

    def __str__(self):
        return self.get_name()


class ProductMatch(BaseModel):
    """
    Learning cache that maps raw text to a catalog product.
    Global for all users.
    """
    raw_name        = models.CharField(max_length=255, db_index=True)
    catalog_product = models.ForeignKey(ProductCatalog, on_delete=models.CASCADE, related_name="matches")
    confidence      = models.FloatField(default=1.0)
    source          = models.CharField(max_length=20, choices=MatchSource.choices, default=MatchSource.AI)
    confirmed_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "product_matches"
        unique_together = [("raw_name", "catalog_product")]
        indexes = [
            models.Index(fields=["raw_name"]),
            models.Index(fields=["-confirmed_count"]),
        ]

    def __str__(self):
        return f'"{self.raw_name}" → {self.catalog_product}'