import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    push_token = models.CharField(max_length=255, blank=True, null=True)
    alert_days_before = models.PositiveSmallIntegerField(default=3)
    language = models.CharField(max_length=5, default="es")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.email
