from django.urls import path

from .views import (
    DocumentVerificationView,
    DocumentVerificationHistoryView,
)


urlpatterns = [
    path(
        "documents/<int:document_id>/verify/",
        DocumentVerificationView.as_view(),
        name="document-verification",
    ),

    path(
        "documents/<int:document_id>/verification-history/",
        DocumentVerificationHistoryView.as_view(),
        name="document-verification-history",
    ),
]