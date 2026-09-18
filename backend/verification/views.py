from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from documents.models import EmployeeDocument
from documents.services import (
    update_travel_request_document_status,
)

from .models import Verification
from .serializers import VerificationSerializer
from users.permissions import IsReviewerOrManager


class DocumentVerificationView(APIView):

    permission_classes = [IsReviewerOrManager]

    def post(self, request, document_id):

        document = get_object_or_404(
            EmployeeDocument,
            id=document_id,
        )

        # -------------------------------------------------
        # Only documents waiting for review can be
        # approved or rejected.
        #
        # This prevents an old VERIFIED or REJECTED
        # document from being verified again.
        # -------------------------------------------------

        if document.status not in (
            EmployeeDocument.Status.UPLOADED,
            EmployeeDocument.Status.PENDING_REVIEW,
        ):
            return Response(
                {
                    "detail": (
                        "Only documents awaiting "
                        "review can be verified."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        verification_status = request.data.get(
            "status"
        )

        comments = request.data.get(
            "comments",
            "",
        )

        # -------------------------------------------------
        # Validate verification status
        # -------------------------------------------------

        if verification_status not in (
            Verification.Status.APPROVED,
            Verification.Status.REJECTED,
        ):
            return Response(
                {
                    "detail": (
                        "Status must be APPROVED "
                        "or REJECTED."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -------------------------------------------------
        # Rejection comments are mandatory
        # -------------------------------------------------

        if (
            verification_status
            == Verification.Status.REJECTED
            and not comments.strip()
        ):
            return Response(
                {
                    "detail": (
                        "Comments are required "
                        "when rejecting a document."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        reviewer = request.user

        # -------------------------------------------------
        # Create verification history record
        # -------------------------------------------------

        verification = Verification.objects.create(
            document=document,
            reviewer=reviewer,
            status=verification_status,
            comments=comments,
        )

        # -------------------------------------------------
        # Update current document status
        # -------------------------------------------------

        if (
            verification_status
            == Verification.Status.APPROVED
        ):

            document.status = (
                EmployeeDocument.Status.VERIFIED
            )

        else:

            document.status = (
                EmployeeDocument.Status.REJECTED
            )

        document.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        # -------------------------------------------------
        # Recalculate travel-request document status
        # -------------------------------------------------

        update_travel_request_document_status(
            document.travel_request
        )

        serializer = VerificationSerializer(
            verification
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )


class DocumentVerificationHistoryView(APIView):

    permission_classes = [IsReviewerOrManager]

    def get(self, request, document_id):

        document = get_object_or_404(
            EmployeeDocument,
            id=document_id,
        )

        # -------------------------------------------------
        # Find all versions of this document type
        # belonging to the same travel request.
        #
        # This preserves the audit trail when an
        # employee replaces a rejected document.
        # -------------------------------------------------

        document_versions = (
            EmployeeDocument.objects
            .filter(
                travel_request=document.travel_request,
                document_type=document.document_type,
            )
            .order_by(
                "-uploaded_at",
                "-id",
            )
        )

        verifications = (
            Verification.objects
            .filter(
                document__in=document_versions
            )
            .select_related(
                "reviewer",
                "document",
            )
            .order_by(
                "-verified_at",
                "-id",
            )
        )

        serializer = VerificationSerializer(
            verifications,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )