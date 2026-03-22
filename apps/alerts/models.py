from django.conf import settings
from django.db import models

from common.models import BaseModel
from .choices import AlertType


class Alert(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="alerts")
    user_product = models.ForeignKey("pantry.UserProduct", on_delete=models.CASCADE, related_name="alerts")
    alert_type = models.CharField(max_length=20, choices=AlertType.choices)
    trigger_date = models.DateField()
    sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    dismissed = models.BooleanField(default=False)
    dismissed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "alerts"
        indexes = [
            models.Index(fields=["trigger_date", "sent"]),
            models.Index(fields=["user", "sent", "dismissed"]),
        ]

    def __str__(self):
        return f"{self.alert_type} · {self.user_product.display_name}"
