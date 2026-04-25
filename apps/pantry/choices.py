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
    WASTED = "wasted", "Wasted"


class Storage(models.TextChoices):
    """Where the user stores this line (drives hint tables and is_frozen sync)."""

    PANTRY = "pantry", "Pantry"
    FRIDGE = "fridge", "Fridge"
    FREEZER = "freezer", "Freezer"
