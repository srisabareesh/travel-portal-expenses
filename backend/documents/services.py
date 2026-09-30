from travel.services import (
    is_legacy_status,
    is_legacy_travel_type,
    Status,
)

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
       DOCUMENTS_PENDING (DOCUMENT_PENDING for
       legacy travel types).

    2. If all mandatory documents are present
       and one or more are waiting for review:
       DOCUMENTS_UNDER_REVIEW.

    3. If all mandatory documents are verified:
       the request advances to MANAGER_APPROVAL
       when it is still inside the document stages
       (new workflows). Legacy travel-type records
       keep DOCUMENT_VERIFICATION: the old flow has
       no manager-approval stage.

    4. If a mandatory document is rejected:
       DOCUMENTS_UNDER_REVIEW. The employee can
       replace it.

    The vocabulary is chosen from the TRAVEL TYPE,
    not from the current status: SUBMITTED is a
    shared value used by both the legacy and the new
    lifecycles, so it cannot discriminate. Historical
    requests with a legacy travel type keep receiving
    legacy document statuses; new requests always
    receive new ones.
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
    all_verified = bool(mandatory_requirements)

    for requirement in mandatory_requirements:

        document = uploaded_documents.get(
            requirement.document_type_id
        )

        if document is None:
            has_missing = True
            all_verified = False
            continue

        if (
            document.status
            == "REJECTED"
        ):
            all_verified = False

        elif document.status in (
            "UPLOADED",
            "PENDING_REVIEW",
        ):
            has_pending_review = True
            all_verified = False

        elif document.status != "VERIFIED":
            all_verified = False

    ##Phase 3.9: requests with a legacy travel type
    ##(historical records) keep the legacy document
    ##statuses; new DOMESTIC/INTERNATIONAL requests
    ##always use the new vocabulary. The travel type is
    ##the reliable discriminator - SUBMITTED is shared
    ##by both lifecycles and cannot be used here.
    use_new_vocabulary = not is_legacy_travel_type(
        travel_request.travel_type
    )

    if use_new_vocabulary:

        pending_status = Status.DOCUMENTS_PENDING

        review_status = Status.DOCUMENTS_UNDER_REVIEW

    else:

        pending_status = Status.DOCUMENT_PENDING

        review_status = Status.DOCUMENT_VERIFICATION

    ##The document stages this request can legally be in,
    ##in its own vocabulary. A request that has already
    ##moved past the document workflow (manager approval
    ##and later) must never be pulled backwards by a late
    ##document event, so its status is left untouched.
    document_stage_statuses = (
        pending_status,
        review_status,
        Status.SUBMITTED,
    )

    if (
        travel_request.status
        not in document_stage_statuses
    ):
        return travel_request.status

    if has_missing:

        new_status = pending_status

    elif has_pending_review:

        new_status = review_status

    else:

        new_status = review_status

        ##All mandatory documents are verified: a request
        ##that is still inside the document stages moves
        ##on to manager approval. Requests that already
        ##left the document stages (or legacy records
        ##without a manager-approval stage) are left
        ##where they are.
        if (
            all_verified
            and mandatory_requirements
            and travel_request.status
            in (pending_status, review_status)
            and use_new_vocabulary
        ):
            new_status = Status.MANAGER_APPROVAL

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