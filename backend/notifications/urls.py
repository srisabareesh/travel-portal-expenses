from django.urls import path

from .views import (
    NotificationListView,
    NotificationMarkReadView,
)


urlpatterns = [
    path(
        "notifications/",
        NotificationListView.as_view(),
        name="notifications",
    ),
    path(
        "notifications/<int:notification_id>/read/",
        NotificationMarkReadView.as_view(),
        name="notification-read",
    ),
]
