from rest_framework import serializers
from .models import Alert
from apps.pantry.serializers import UserProductSerializer


class AlertSerializer(serializers.ModelSerializer):
    user_product = UserProductSerializer(read_only=True)

    class Meta:
        model = Alert
        fields = [
            "id", "user_product", "alert_type",
            "trigger_date", "sent", "dismissed", "created_at",
        ]
        read_only_fields = ["id", "sent", "created_at"]
