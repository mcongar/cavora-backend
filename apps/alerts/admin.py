from django.contrib import admin
from .models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display  = ["user", "alert_type", "trigger_date", "sent", "dismissed"]
    list_filter   = ["alert_type", "sent", "dismissed"]
    search_fields = ["user__email"]