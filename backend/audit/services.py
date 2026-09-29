from .models import AuditLog


def log_action(
    user,
    action,
    travel_request=None,
    object_repr="",
    previous_value="",
    new_value="",
    comment="",
    metadata=None,
):
    """
    Record an audit log entry for a business action.

    Never raises: auditing must not break business flows.
    """

    try:

        return AuditLog.objects.create(
            user=user if (
                user is not None and user.is_authenticated
            ) else None,
            action=action,
            travel_request=travel_request,
            object_repr=object_repr or (
                str(travel_request)
                if travel_request is not None
                else ""
            ),
            previous_value=str(previous_value or ""),
            new_value=str(new_value or ""),
            comment=comment,
            metadata=metadata or {},
        )

    except Exception:

        return None
