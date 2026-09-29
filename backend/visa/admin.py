from django.contrib import admin

from .models import Visa


@admin.register(Visa)
class VisaAdmin(admin.ModelAdmin):

    list_display = (
        "travel_request",
        "state",
        "country",
        "applied_on",
        "decided_by",
        "decision_at",
    )

    list_filter = (
        "state",
        "country",
    )

    search_fields = (
        "travel_request__request_number",
        "country",
    )
