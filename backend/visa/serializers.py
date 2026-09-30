from rest_framework import serializers

from .models import Visa


class VisaSerializer(serializers.ModelSerializer):

    decided_by_name = serializers.SerializerMethodField()

    def get_decided_by_name(self, obj):
        user = obj.decided_by

        if user is None:
            return ""

        full_name = (
            user.get_full_name() or ""
        ).strip()

        return full_name or user.get_username()

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
