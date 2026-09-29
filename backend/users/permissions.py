from rest_framework.permissions import BasePermission

from .models import Role


class IsAdmin(BasePermission):
    """
    Grants administrative/configuration access only.

    Membership in the ADMIN role does NOT implicitly grant
    MANAGER or REVIEWER business authority: those capabilities
    require the corresponding role to be explicitly assigned.
    """


    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.has_role(Role.Name.ADMIN)
        )


class IsReviewer(BasePermission):
    """
    Grants document-verification / HR authority.

    Requires explicit REVIEWER membership. ADMIN alone is
    not sufficient.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.has_role(Role.Name.REVIEWER)
        )


class IsManager(BasePermission):
    """
    Grants business approval authority.

    Requires explicit MANAGER membership. ADMIN alone is
    not sufficient.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.has_role(Role.Name.MANAGER)
        )


class IsEmployee(BasePermission):
    """
    Grants employee self-service authority (own requests,
    document uploads, expenses).

    Requires explicit EMPLOYEE membership.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.has_role(Role.Name.EMPLOYEE)
        )


class IsReviewerOrManager(BasePermission):
    """
    Grants reviewer OR manager authority when the
    corresponding role has been explicitly assigned.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.has_any_role(
                Role.Name.REVIEWER,
                Role.Name.MANAGER,
            )
        )
