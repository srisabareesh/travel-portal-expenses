from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, Role


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
    )


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

    ##`roles` is the source of truth for authorization;
    ##`role` is the legacy field kept in sync automatically.
    filter_horizontal = UserAdmin.filter_horizontal + (
        "roles",
    )

    fieldsets = UserAdmin.fieldsets + (
        (
            "Employee Information",
            {
                "fields": (
                    "employee_id",
                    "department",
                    "role",
                    "roles",
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
                    "roles",
                    "manager",
                ),
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        """
        On existing users, protect the employee ID and the
        legacy role field from accidental manual overwrite:
        employee IDs must never change, and `role` is
        synchronized from `roles` automatically.

        When creating a user, `employee_id` stays editable so
        an admin may explicitly assign a custom ID; leaving it
        blank triggers automatic EMP-###### generation.
        """
        readonly = list(
            super().get_readonly_fields(request, obj)
        )

        if obj:  ##editing an existing user
            readonly += ["employee_id", "role"]

        return readonly
