from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver

from .models import User, Role
from .services import sync_legacy_role

##Legacy role synchronization
##---------------------------
##User.roles (M2M) is the source of truth for authorization.
##The legacy User.role CharField is kept temporarily for
##backward compatibility and is kept in sync automatically:

##  * On first save of a user with no roles yet, the user
##    receives the role matching the legacy field's value
##    (default EMPLOYEE), so existing creation paths —
##    Django admin, shell, tests, fixtures — continue to
##    work exactly as before.

##  * Whenever User.roles changes, the legacy field is
##    re-synced to the highest-priority role
##    (ADMIN > MANAGER > REVIEWER > EMPLOYEE).

##The legacy field must never be treated as an independent
##source of truth: all permission checks use has_role().


@receiver(post_save, sender=User)
def bootstrap_legacy_role(sender, instance, created, **kwargs):
    ##Runs after every save. For newly created users without
    ##any assigned roles, create the matching Role membership
    ##from the legacy field value (back-compat with existing
    ##user-creation code paths).
    if created and not instance.roles.exists():
        legacy_value = instance.role or Role.Name.EMPLOYEE

        valid_names = set(Role.Name.values)

        if legacy_value not in valid_names:
            legacy_value = Role.Name.EMPLOYEE

        role = Role.objects.filter(name=legacy_value).first()

        if role is None:
            from .services import ensure_roles_seeded

            ensure_roles_seeded()
            role = Role.objects.get(name=legacy_value)

        instance.roles.add(role)

        sync_legacy_role(instance)


@receiver(m2m_changed, sender=User.roles.through)
def sync_legacy_role_on_change(sender, instance, action, pk_set, **kwargs):
    ##Re-sync the legacy role field whenever role membership
    ##changes (add/remove/clear) on a saved user.
    if action in ("post_add", "post_remove", "post_clear"):
        if instance.pk:
            sync_legacy_role(instance)
