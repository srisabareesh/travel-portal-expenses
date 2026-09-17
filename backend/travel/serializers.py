from rest_framework import serializers
from .models import Country,TravelRequest

class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model= Country
        fields = (
            "id",
            "name",
            "country_code",
            "is_active",
        )

class TravelRequestSerializer(serializers.ModelSerializer):

    employee_name = serializers.CharField(
        source="employee.get_full_name",
        read_only=True,
    )

    country_name = serializers.CharField(
        source="destination_country.name",
        read_only=True,
    )

    class Meta:
        model = TravelRequest
        fields = (
            "id",
            "request_number",
            "employee",
            "employee_name",
            "destination_country",
            "country_name",
            "destination_city",
            "client",
            "project",
            "travel_type",
            "start_date",
            "end_date",
            "purpose",
            "status",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "employee",
            "request_number",
            "status",
            "created_at",
            "updated_at",
            )