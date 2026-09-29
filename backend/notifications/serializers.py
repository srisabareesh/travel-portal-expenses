from rest_framework import serializers

from .models import Notification


class NotificationSerializer(
    serializers.ModelSerializer
):

    recipient_name = serializers.CharField(
        source="recipient.get_full_name",
        read_only=True,
    )

    class Meta:
        model = Notification

        fields = (
            "id",
            "recipient",
            "recipient_name",
            "event",
            "message",
            "travel_request",
            "is_read",
            "read_at",
            "created_at",
        )

        read_only_fields = fields
