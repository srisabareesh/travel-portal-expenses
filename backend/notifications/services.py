from .models import Notification


def notify(
    recipient,
    event,
    message,
    travel_request=None,
):
    """
    Create an in-app notification for a single recipient.

    Safe to call with recipient=None (no-op) so callers do
    not need to guard against missing related users.
    """

    if recipient is None:
        return None

    return Notification.objects.create(
        recipient=recipient,
        event=event,
        message=message,
        travel_request=travel_request,
    )


def notify_manager_approval_required(travel_request):
    """
    Notify the employee's manager that a request is
    awaiting their approval.
    """

    manager = travel_request.employee.manager

    if manager is None:
        return None

    return notify(
        recipient=manager,
        event="MANAGER_APPROVAL_REQUIRED",
        message=(
            f"Travel request "
            f"{travel_request.request_number} is waiting "
            f"for your approval."
        ),
        travel_request=travel_request,
    )


def notify_request_status_change(
    travel_request,
    event,
    message,
):
    """Notify the employee about their request's status."""

    return notify(
        recipient=travel_request.employee,
        event=event,
        message=message,
        travel_request=travel_request,
    )
