from django.utils import timezone

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(
            recipient=request.user,
        )[:100]

        serializer = NotificationSerializer(
            notifications,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class NotificationMarkReadView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id):
        notification = Notification.objects.filter(
            id=notification_id,
            recipient=request.user,
        ).first()

        if notification is None:
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(
                update_fields=[
                    "is_read",
                    "read_at",
                ]
            )

        serializer = NotificationSerializer(
            notification
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
