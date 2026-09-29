from rest_framework import serializers

from .models import Visa


class VisaSerializer(serializers.ModelSerializer):

    decided_by_name = serializers.CharField(
        source="decided_by.get_full_name",
        read_only=True,
    )

    class Meta:
        model = Visa

        fields = (
            "id",
            "travel_request",
            "state",
            "country",
            "applied_on",
            "decision_at",
            "decided_by",
            "decided_by_name",
            "remarks",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "travel_request",
            "state",
            "decision_at",
            "decided_by",
            "created_at",
            "updated_at",
        )
