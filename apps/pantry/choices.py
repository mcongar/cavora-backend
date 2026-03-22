from django.db import models


class AddMethod(models.TextChoices):
    BARCODE = "barcode", "Barcode"
    TICKET = "ticket", "Ticket"
    MANUAL = "manual", "Manual"


class ProductStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    CONSUMED = "consumed", "Consumed"
    EXPIRED = "expired", "Expired"
    REMOVED = "removed", "Removed"
