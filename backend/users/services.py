"""
Service layer for user/role operations.

Role system:
    User.roles (M2M to users.Role) is the source of truth
    for authorization. The legacy User.role CharField is kept
    temporarily for backward compatibility and is always kept
    in sync via sync_legacy_role(); it must never be treated as
    an independent source of truth.

Employee ID:
    New users automatically receive a sequential ID of the form
    EMP-000001. Existing values are never overwritten and are
    never released when a user is deactivated.
"""

import re
import time

from django.db import IntegrityError, transaction

from .models import Role, User

# Matches exactly the system-generated format, e.g. EMP-000042.
SYSTEM_EMPLOYEE_ID_PATTERN = re.compile(r"^EMP-(\d{6,})$")

# Priority used to choose the single legacy `role` value when a
# user holds multiple roles. Highest priority first.
LEGACY_ROLE_PRIORITY = (
    Role.Name.ADMIN,
    Role.Name.MANAGER,
    Role.Name.REVIEWER,
    Role.Name.EMPLOYEE,
)


def ensure_roles_seeded():
    """
    Make sure the four standard role rows exist.

    Used by the seed migration and safely callable at runtime
    (e.g. from management commands). Idempotent.
    """
    descriptions = {
        Role.Name.EMPLOYEE: "Creates travel requests and expenses.",
        Role.Name.REVIEWER: "HR/Reviewer: document verification, bookings, expenses.",
        Role.Name.MANAGER: "Approves team travel requests and settlements.",
        Role.Name.ADMIN: "Administrative and configuration access only.",
    }

    for name in Role.Name.values:
        Role.objects.get_or_create(
            name=name,
            defaults={"description": descriptions.get(name, "")},
        )


def assign_role(user, role_name):
    """
    Explicitly assign a role to a user.

    Idempotent: assigning an already-held role does nothing.
    Duplicate membership is prevented both here and by the
    database-level unique constraint on the through table.

    Keeps the legacy User.role field in sync and returns whether
    the role was newly added.
    """
    ensure_roles_seeded()

    role = Role.objects.get(name=role_name)

    with transaction.atomic():
        if not user.roles.filter(pk=role.pk).exists():
            user.roles.add(role)
            added = True
        else:
            added = False

        sync_legacy_role(user)

    return added


def sync_legacy_role(user):
    """
    Keep the legacy User.role CharField aligned with User.roles.

    Synchronization strategy:
      * User.roles (M2M) is the source of truth.
      * If the user has no roles at all, the legacy field is
        cleared to "" (never silently re-adds a stale role).
      * If the user has roles, the legacy field is set to the
        highest-priority role (ADMIN > MANAGER > REVIEWER >
        EMPLOYEE) so legacy code paths and the Django admin
        keep working predictably.

    Call sites:
      * post_save signal (legacy bootstrap + normal saves)
      * m2m_changed signal on User.roles (assignment changes)
      * users.services.assign_role()
    """
    highest = next(
        (
            name
            for name in LEGACY_ROLE_PRIORITY
            if user.roles.filter(name=name).exists()
        ),
        None,
    )

    legacy_value = highest or ""

    if user.role != legacy_value:
        User.objects.filter(pk=user.pk).update(role=legacy_value)
        # Keep the in-memory instance consistent.
        user.role = legacy_value


def generate_employee_id():
    """
    Generate the next sequential employee ID (EMP-000001, ...).

    Concurrency strategy:

    1. SQLite (current development environment):
       Django wraps each save() in a transaction and SQLite
       serialises writers with a database-wide write lock, so
       two concurrent creates cannot both commit the same
       generated ID. A short retry loop recomputes the next
       number from the committed rows if an IntegrityError
       races anyway (the `employee_id` column has a UNIQUE
       constraint, which is the final guarantee).

    2. PostgreSQL (future):
       Retrying on IntegrityError against the UNIQUE constraint
       is correct there too. For high-volume signup the same
       function can later be upgraded to SELECT ... FOR UPDATE
       on a counter row or a Postgres sequence without changing
       any caller.

    IDs are only ever derived from the maximum existing
    system-generated number, so numbers are never reused even
    when users are deactivated.
    """

    for _attempt in range(5):
        max_number = 0

        for employee_id in User.objects.exclude(
            employee_id=""
        ).values_list("employee_id", flat=True):
            match = SYSTEM_EMPLOYEE_ID_PATTERN.match(employee_id)

            if match:
                max_number = max(max_number, int(match.group(1)))

        candidate = f"EMP-{max_number + 1:06d}"

        if not User.objects.filter(employee_id=candidate).exists():
            return candidate

        # Another writer claimed the candidate between the two
        # queries: loop and recompute.
        time.sleep(0.05)

    raise RuntimeError(
        "Could not generate a unique employee ID "
        "after multiple attempts."
    )


def create_user_with_generated_id(username, password=None, **extra_fields):
    """
    Convenience helper for creating users with an automatically
    generated employee ID inside a single transaction.

    User.save() also auto-fills a blank employee_id, so ordinary
    creation paths (Django admin, fixtures, tests) are covered
    without calling this helper explicitly.
    """
    with transaction.atomic():
        user = User(username=username, **extra_fields)

        if password:
            user.set_password(password)

        user.save()

        return user
