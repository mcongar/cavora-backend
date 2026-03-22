from django.db import models


class AlertType(models.TextChoices):
    EXPIRY_SOON = "expiry_soon", "Expiry Soon"
    EXPIRY_TODAY = "expiry_today", "Expiry Today"
    EXPIRED = "expired", "Expired"
