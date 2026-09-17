from django.contrib import admin

from .models import DocumentType, DocumentRequirement, EmployeeDocument

# Register your models here.
@admin.register(DocumentType)

class DocumentTypeAdmin(admin.ModelAdmin):
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

@admin.register(DocumentRequirement)
class DocumentRequirementAdmin(admin.ModelAdmin):
    list_display = (
        "country",
        "document_type",
        "travel_type",
        "mandatory",
        "is_active",
    )

    list_filter = (
        "country",
        "travel_type",
        "mandatory",
        "is_active",
    )

    search_fields = (
        "country__name",
        "document_type__name",
    )

@admin.register(EmployeeDocument)
class EmployeeDocumentAdmin(admin.ModelAdmin):

    list_display = (
        "travel_request",
        "document_type",
        "status",
        "issue_date",
        "expiry_date",
        "uploaded_by",
        "uploaded_at",
    )

    list_filter = (
        "status",
        "document_type",
    )

    search_fields = (
        "travel_request__request_number",
        "travel_request__employee__employee_id",
        "document_type__name",
    )

    readonly_fields = (
        "uploaded_at",
        "updated_at",
    )