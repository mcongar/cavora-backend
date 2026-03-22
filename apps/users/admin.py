from django.contrib.auth.admin import UserAdmin
from django.contrib import admin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display  = ["email", "username", "alert_days_before", "push_token", "is_staff"]
    search_fields = ["email", "username"]
    fieldsets = UserAdmin.fieldsets + (
        ("Cavora", {"fields": ("push_token", "alert_days_before")}),
    )