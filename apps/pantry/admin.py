from django.contrib import admin
from .models import ScanSession, UserProduct


@admin.register(ScanSession)
class ScanSessionAdmin(admin.ModelAdmin):
    list_display  = ["user", "method", "products_count", "label", "created_at"]
    list_filter   = ["method"]
    search_fields = ["user__email", "label"]


@admin.register(UserProduct)
class UserProductAdmin(admin.ModelAdmin):
    list_display  = ["user", "display_name", "status", "expiry_date", "expiry_estimated", "add_method"]
    list_filter   = ["status", "add_method", "expiry_estimated"]
    search_fields = ["user__email", "name_override"]