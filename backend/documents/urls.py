from django.urls import path

from .views import (
    TravelRequestDocumentChecklistView,
    EmployeeDocumentUploadView,
)


urlpatterns = [

    path(
        "travel-requests/<int:travel_request_id>/documents/",
        TravelRequestDocumentChecklistView.as_view(),
        name="travel-request-document-checklist",
    ),

    path(
        "travel-requests/<int:travel_request_id>/documents/upload/",
        EmployeeDocumentUploadView.as_view(),
        name="employee-document-upload",
    ),
]