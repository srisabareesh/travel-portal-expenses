from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):

    list_display = (
        "action",
        "user",
        "travel_request",
        "previous_value",
        "new_value",
        "created_at",
    )

    list_filter = ("action", "created_at")

    search_fields = (
        "user__username",
        "travel_request__request_number",
        "action",
    )

    readonly_fields = (
        "user",
        "action",
        "travel_request",
        "object_repr",
        "previous_value",
        "new_value",
        "comment",
        "metadata",
        "created_at",
    )

    ##Audit records must not be modified or deleted
    ##through the admin.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
