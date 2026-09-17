from datetime import date

from .models import DocumentRequirement


def get_required_documents(travel_request):
    """
    Return the document requirements applicable
    to a specific travel request.
    """

    duration_days = (
        travel_request.end_date
        - travel_request.start_date
    ).days + 1

    requirements = DocumentRequirement.objects.filter(
        country=travel_request.destination_country,
        travel_type=travel_request.travel_type,
        is_active=True,
    )

    applicable_requirements = []

    for requirement in requirements:

        if (
            requirement.minimum_duration_days is not None
            and duration_days < requirement.minimum_duration_days
        ):
            continue

        if (
            requirement.maximum_duration_days is not None
            and duration_days > requirement.maximum_duration_days
        ):
            continue

        applicable_requirements.append(requirement)

    return applicable_requirements

def get_document_checklist(travel_request):
    """
    Return required documents along with
    their current upload status.
    """

    requirements = get_required_documents(travel_request)

    uploaded_documents = {
        document.document_type_id: document
        for document in travel_request.documents.all()
    }

    checklist = []

    for requirement in requirements:

        document = uploaded_documents.get(
            requirement.document_type_id
        )

        if document is None:
            status = "MISSING"
        else:
            status = document.status

        checklist.append(
            {
                "document_type": requirement.document_type.name,
                "document_type_id": requirement.document_type.id,
                "mandatory": requirement.mandatory,
                "status": status,
                "document_id": (
                    document.id
                    if document
                    else None
                ),
                "file": (
                    document.file.url
                    if document and document.file
                    else None
                ),
                "issue_date": (
                    document.issue_date
                    if document
                    else None
                ),
                "expiry_date": (
                    document.expiry_date
                    if document
                    else None
                ),
            }
        )

    return checklist

def update_travel_request_document_status(travel_request):
    """
    Update the travel request status based on
    the status of its required documents.

    Rules:

    1. If any mandatory document is missing,
       the request is DOCUMENT_PENDING.

    2. If all mandatory documents are present
       but one or more are waiting for review,
       the request is DOCUMENT_VERIFICATION.

    3. If all mandatory documents are verified,
       the request remains DOCUMENT_VERIFICATION
       until a Manager makes the final decision.

    4. If a mandatory document is rejected,
       the request remains DOCUMENT_VERIFICATION
       so the employee can replace/re-upload it.
    """

    requirements = get_required_documents(
        travel_request
    )

    mandatory_requirements = [
        requirement
        for requirement in requirements
        if requirement.mandatory
    ]

    uploaded_documents = {
        document.document_type_id: document
        for document in travel_request.documents.all()
    }

    has_missing = False
    has_pending_review = False
    has_rejected = False

    for requirement in mandatory_requirements:

        document = uploaded_documents.get(
            requirement.document_type_id
        )

        if document is None:
            has_missing = True
            continue

        if document.status == "REJECTED":
            has_rejected = True

        elif document.status in (
            "UPLOADED",
            "PENDING_REVIEW",
        ):
            has_pending_review = True

    if has_missing:
        new_status = (
            travel_request.Status.DOCUMENT_PENDING
        )

    elif has_pending_review:
        new_status = (
            travel_request.Status.DOCUMENT_VERIFICATION
        )

    elif has_rejected:
        new_status = (
            travel_request.Status.DOCUMENT_VERIFICATION
        )

    else:
        new_status = (
            travel_request.Status.DOCUMENT_VERIFICATION
        )

    if travel_request.status != new_status:

        travel_request.status = new_status

        travel_request.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

    return new_status

def are_all_mandatory_documents_verified(travel_request):
    """
    Return True when every mandatory document
    required for the travel request exists and
    has been verified.
    """

    requirements = get_required_documents(
        travel_request
    )

    mandatory_requirements = [
        requirement
        for requirement in requirements
        if requirement.mandatory
    ]

    # If there are no mandatory requirements,
    # there is nothing that needs verification.
    if not mandatory_requirements:
        return True

    uploaded_documents = {
        document.document_type_id: document
        for document in travel_request.documents.all()
    }

    for requirement in mandatory_requirements:

        document = uploaded_documents.get(
            requirement.document_type_id
        )

        if document is None:
            return False

        if (
            document.status
            != "VERIFIED"
        ):
            return False

    return True