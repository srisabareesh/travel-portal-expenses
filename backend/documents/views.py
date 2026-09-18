from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import (
    MultiPartParser,
    FormParser,
)

from travel.models import TravelRequest

from .models import EmployeeDocument
from .serializers import (
    DocumentChecklistSerializer,
    EmployeeDocumentSerializer,
)
from .services import (
    get_document_checklist,
    get_required_documents,
    update_travel_request_document_status,
    are_all_mandatory_documents_verified,
)
from users.permissions import IsEmployee


def can_access_travel_request(user, travel_request):
    """
    Check whether the logged-in user can access
    a specific travel request.

    Rules:

    EMPLOYEE:
        Can access only their own request.

    REVIEWER:
        Can access reviewer workflow requests.

    MANAGER:
        Can access requests belonging to their team.

    ADMIN:
        Can access all requests.
    """

    if user.role == "ADMIN":
        return True

    if user.role == "EMPLOYEE":
        return travel_request.employee == user

    if user.role == "REVIEWER":
        return travel_request.status in (
            TravelRequest.Status.DOCUMENT_PENDING,
            TravelRequest.Status.DOCUMENT_VERIFICATION,
        )

    if user.role == "MANAGER":
        return travel_request.employee.manager == user

    return False


class TravelRequestDocumentChecklistView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, travel_request_id):

        travel_request = get_object_or_404(
            TravelRequest,
            id=travel_request_id,
        )

        if not can_access_travel_request(
            request.user,
            travel_request,
        ):
            return Response(
                {
                    "detail": (
                        "You do not have permission "
                        "to view this travel request."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        checklist = get_document_checklist(
            travel_request
        )

        all_mandatory_verified = (
            are_all_mandatory_documents_verified(
                travel_request
            )
        )

        serializer = DocumentChecklistSerializer(
            checklist,
            many=True,
        )

        return Response(
            {
                "checklist": serializer.data,
                "all_mandatory_verified": (
                    all_mandatory_verified
                ),
            },
            status=status.HTTP_200_OK,
        )


class EmployeeDocumentUploadView(GenericAPIView):

    serializer_class = EmployeeDocumentSerializer

    permission_classes = [
        IsAuthenticated,
        IsEmployee,
    ]

    parser_classes = (
        MultiPartParser,
        FormParser,
    )

    def post(self, request, travel_request_id):

        travel_request = get_object_or_404(
            TravelRequest,
            id=travel_request_id,
        )

        # Employee can upload documents only
        # for their own travel requests.
        if travel_request.employee != request.user:
            return Response(
                {
                    "detail": (
                        "You do not have permission "
                        "to upload documents for this "
                        "travel request."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # -------------------------------------------------
        # 1. Validate document_type
        # -------------------------------------------------

        document_type_id = request.data.get(
            "document_type"
        )

        if not document_type_id:
            return Response(
                {
                    "document_type": (
                        "Document type is required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            document_type_id = int(
                document_type_id
            )

        except (TypeError, ValueError):
            return Response(
                {
                    "document_type": (
                        "Invalid document type."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -------------------------------------------------
        # 2. Check whether this document is required
        #    for this travel request
        # -------------------------------------------------

        requirements = get_required_documents(
            travel_request
        )

        requirement = next(
            (
                requirement
                for requirement in requirements
                if requirement.document_type_id
                == document_type_id
            ),
            None,
        )

        if requirement is None:
            return Response(
                {
                    "document_type": (
                        "This document is not required "
                        "for this travel request."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -------------------------------------------------
        # 3. Check latest existing document
        # -------------------------------------------------

        existing_document = (
            EmployeeDocument.objects
            .filter(
                travel_request=travel_request,
                document_type_id=document_type_id,
            )
            .order_by(
                "-uploaded_at",
                "-id",
            )
            .first()
        )

        if existing_document:

            # ---------------------------------------------
            # VERIFIED document cannot be replaced
            # ---------------------------------------------

            if (
                existing_document.status
                == EmployeeDocument.Status.VERIFIED
            ):
                return Response(
                    {
                        "document_type": (
                            "This document has already "
                            "been verified and cannot "
                            "be replaced."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # ---------------------------------------------
            # Document already waiting for review
            # ---------------------------------------------

            if (
                existing_document.status
                in (
                    EmployeeDocument.Status.UPLOADED,
                    EmployeeDocument.Status.PENDING_REVIEW,
                )
            ):
                return Response(
                    {
                        "document_type": (
                            "This document is already "
                            "awaiting review."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # ---------------------------------------------
            # Only REJECTED documents can be re-uploaded
            # ---------------------------------------------

            if (
                existing_document.status
                != EmployeeDocument.Status.REJECTED
            ):
                return Response(
                    {
                        "document_type": (
                            "This document cannot "
                            "be uploaded again "
                            "in its current status."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # -------------------------------------------------
        # 4. Validate uploaded file and dates
        # -------------------------------------------------

        serializer = self.get_serializer(
            data=request.data
        )

        if serializer.is_valid():

            # -------------------------------------------------
            # 5. Create a NEW document
            #
            # The old REJECTED document is preserved.
            # -------------------------------------------------

            document = serializer.save(
                travel_request=travel_request,
                uploaded_by=request.user,
                status=(
                    EmployeeDocument.Status.PENDING_REVIEW
                ),
            )

            # -------------------------------------------------
            # 6. Recalculate travel request status
            # -------------------------------------------------

            update_travel_request_document_status(
                travel_request
            )

            response_serializer = (
                EmployeeDocumentSerializer(
                    document
                )
            )

            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED,
            )

        # -------------------------------------------------
        # 7. Return serializer validation errors
        # -------------------------------------------------

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )