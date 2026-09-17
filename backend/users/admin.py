from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)   ##Registers your custom User model with Django Admin.
class CustomUserAdmin(UserAdmin):   ##Creates your own Admin configuration by inheriting from Django's UserAdmin

    list_display = (
        "username",
        "employee_id",
        "email",
        "department",
        "role",
        "is_active",
    )

    list_filter = (
        "role",
        "department",
        "is_active",
    )

    search_fields = (
        "username",
        "employee_id",
        "email",
        "first_name",
        "last_name",
    )

    fieldsets = UserAdmin.fieldsets + (
        (
            "Employee Information",
            {
                "fields": (
                    "employee_id",
                    "department",
                    "role",
                    "manager",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "password1",
                    "password2",
                ),
            },
        ),
        (
            "Employee Information",
            {
                "fields": (
                    "employee_id",
                    "department",
                    "role",
                    "manager",
                ),
            },
        ),
    )