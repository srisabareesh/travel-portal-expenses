from rest_framework import serializers

from .models import Verification


class VerificationSerializer(serializers.ModelSerializer):

    reviewer_name = serializers.CharField(
        source="reviewer.get_full_name",
        read_only=True,
    )

    class Meta:
        model = Verification
        fields = (
            "id",
            "document",
            "reviewer",
            "reviewer_name",
            "status",
            "comments",
            "verified_at",
        )

        read_only_fields = (
            "reviewer",
            "verified_at",
        )