from django.contrib import admin

from .models import Verification

# Register your models here.

@admin.register(Verification)
class VerificationAdmin(admin.ModelAdmin):

    list_display=(
        "document",
        "reviewer",
        "status",
        "verified_at"
    )
    list_filter=(
        "status",
        "verified_at"
    )
    search_fields = (
        "document__travel_request__request_number",
        "document__travel_request__employee__employee_id",
        "document__document_type__name",
        "reviewer__employee_id",
    )

    readonly_fields = (
        "verified_at",
    )