from django.contrib import admin

from .models import Country, TravelRequest

# Register your models here.

###It controls how Country records appear and can be managed inside /admin/.

@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "country_code",
        "is_active",
        "created_at",
    )

    list_filter= (
        "is_active",
    )

    search_fields=(
        "name",
        "country_code",
    )
@admin.register(TravelRequest)
class TravelRequestAdmin(admin.ModelAdmin):
    list_display = (
        "request_number",
        "employee",
        "destination_country",
        "destination_city",
        "travel_type",
        "start_date",
        "end_date",
        "status",
    )
    list_filter = (
        "status",
        "travel_type",
        "destination_country",
    )

    search_fields = (
        "request_number",
        "employee__employee_id",
        "employee__username",
        "destination_city",
        "client",
        "project",
    )

    readonly_fields = (
        "request_number",
        "created_at",
        "updated_at",
    )