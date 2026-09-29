"""
Seed the four standard roles.

Runs after 0002 creates the Role table, so every environment
(even one created from scratch with `migrate`) automatically
has EMPLOYEE, REVIEWER, MANAGER and ADMIN available for
explicit assignment.

Idempotent: re-running or seeding on a partially-populated
table cannot duplicate rows (get_or_create by unique name).
"""

from django.db import migrations


def seed_roles(apps, schema_editor):
    from users.services import ensure_roles_seeded

    ensure_roles_seeded()


def unseed_roles(apps, schema_editor):
    """
    Reverse migration: remove ONLY the four standard seed
    rows. Roles that were created or renamed by users are
    never touched, and no user data is affected.
    """
    Role = apps.get_model("users", "Role")

    Role.objects.filter(
        name__in=["EMPLOYEE", "REVIEWER", "MANAGER", "ADMIN"]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_role_alter_user_employee_id_alter_user_role_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_roles, unseed_roles),
    ]
