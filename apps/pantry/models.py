from django.conf import settings
from django.db import models

from common.models import BaseModel
from .choices import AddMethod, ProductStatus


class ScanSession(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="scan_sessions")
    method = models.CharField(max_length=20, choices=AddMethod.choices)
    products_count = models.PositiveSmallIntegerField(default=0)
    label = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "scan_sessions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} · {self.method} · {self.products_count} products"


class UserProduct(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="products")
    catalog_product = models.ForeignKey("catalog.ProductCatalog", on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name="user_instances")
    session = models.ForeignKey(ScanSession, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
    name_override = models.CharField(max_length=255, blank=True)
    add_method = models.CharField(max_length=20, choices=AddMethod.choices)
    quantity = models.PositiveSmallIntegerField(default=1)
    unit = models.CharField(max_length=20, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    expiry_estimated = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=ProductStatus.choices, default=ProductStatus.ACTIVE)
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "user_products"
        ordering = ["expiry_date", "created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["user", "expiry_date"]),
        ]

    @property
    def display_name(self):
        if self.catalog_product:
            return str(self.catalog_product)
        return self.name_override or "Unknown product"

    def __str__(self):
        return f"{self.user} · {self.display_name}"
