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

    requirements = (
        DocumentRequirement.objects
        .filter(
            country=travel_request.destination_country,
            travel_type=travel_request.travel_type,
            is_active=True,
        )
        .select_related("document_type")
        .order_by("id")
    )

    applicable_requirements = []

    for requirement in requirements:

        if (
            requirement.minimum_duration_days
            is not None
            and duration_days
            < requirement.minimum_duration_days
        ):
            continue

        if (
            requirement.maximum_duration_days
            is not None
            and duration_days
            > requirement.maximum_duration_days
        ):
            continue

        applicable_requirements.append(
            requirement
        )

    return applicable_requirements


def get_latest_documents_by_type(travel_request):
    """
    Return the latest uploaded EmployeeDocument
    for each document type.

    Documents are ordered from newest to oldest.
    The first document encountered for each
    document type is therefore the latest version.
    """

    uploaded_documents = {}

    documents = (
        travel_request.documents
        .all()
        .order_by(
            "-uploaded_at",
            "-id",
        )
    )

    for document in documents:

        if document.document_type_id not in (
            uploaded_documents
        ):
            uploaded_documents[
                document.document_type_id
            ] = document

    return uploaded_documents


def get_document_checklist(travel_request):
    """
    Return required documents along with
    their current upload status.

    If multiple versions of a document exist,
    the latest uploaded version is used.
    """

    requirements = get_required_documents(
        travel_request
    )

    uploaded_documents = (
        get_latest_documents_by_type(
            travel_request
        )
    )

    checklist = []

    for requirement in requirements:

        document = uploaded_documents.get(
            requirement.document_type_id
        )

        if document is None:
            current_status = "MISSING"
        else:
            current_status = document.status

        checklist.append(
            {
                "document_type": (
                    requirement.document_type.name
                ),
                "document_type_id": (
                    requirement.document_type.id
                ),
                "mandatory": (
                    requirement.mandatory
                ),
                "status": current_status,
                "document_id": (
                    document.id
                    if document
                    else None
                ),
                "file": (
                    document.file.url
                    if document
                    and document.file
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


def update_travel_request_document_status(
    travel_request,
):
    """
    Update the travel request status based on
    the status of its required documents.

    Rules:

    1. If any mandatory document is missing:
       DOCUMENT_PENDING.

    2. If all mandatory documents are present
       and one or more are waiting for review:
       DOCUMENT_VERIFICATION.

    3. If all mandatory documents are verified:
       DOCUMENT_VERIFICATION.

       The Manager still makes the final
       travel-request decision.

    4. If a mandatory document is rejected:
       DOCUMENT_VERIFICATION.

       The employee can replace it.
    """

    requirements = get_required_documents(
        travel_request
    )

    mandatory_requirements = [
        requirement
        for requirement in requirements
        if requirement.mandatory
    ]

    uploaded_documents = (
        get_latest_documents_by_type(
            travel_request
        )
    )

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

        if (
            document.status
            == "REJECTED"
        ):
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

    if (
        travel_request.status
        != new_status
    ):

        travel_request.status = new_status

        travel_request.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

    return new_status


def are_all_mandatory_documents_verified(
    travel_request,
):
    """
    Return True when every mandatory document
    required for the travel request exists and
    the latest version has been verified.
    """

    requirements = get_required_documents(
        travel_request
    )

    mandatory_requirements = [
        requirement
        for requirement in requirements
        if requirement.mandatory
    ]

    if not mandatory_requirements:
        return True

    uploaded_documents = (
        get_latest_documents_by_type(
            travel_request
        )
    )

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