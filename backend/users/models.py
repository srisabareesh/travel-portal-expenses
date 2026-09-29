from django.db import models

from django.contrib.auth.models import AbstractUser  ##imports Django's built-in base class for creating a custom user model.

# Create your models here.

class Role(models.Model):
    """
    A role that can be explicitly assigned to users.

    Roles are the source of truth for authorization:
    a user may hold any combination of roles, and holding
    ADMIN does NOT imply REVIEWER or MANAGER business powers.
    """

    class Name(models.TextChoices):  ##the four standard roles of the portal
        EMPLOYEE = "EMPLOYEE", "Employee"
        REVIEWER = "REVIEWER", "Reviewer / HR"
        MANAGER = "MANAGER", "Manager"
        ADMIN = "ADMIN", "Admin"

    name = models.CharField(
        max_length=20,
        choices=Name.choices,
        unique=True,
    )

    description = models.CharField(
        max_length=200,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return self.get_name_display()


class User(AbstractUser):

    class Role(models.TextChoices):  ##legacy single-role field (kept for backward compatibility)
        EMPLOYEE = "EMPLOYEE", "Employee"   ##"EMPLOYEE"     → value stored in the database
        REVIEWER = "REVIEWER", "Reviewer"   ## "Employee"     → human-readable name shown in forms/adm
        MANAGER = "MANAGER", "Manager"
        ADMIN = "ADMIN", "Admin"

    employee_id= models.CharField(
        max_length=20,
        unique=True,
        blank=True,   ##auto-generated (EMP-000001) by User.save() when blank
    )

    department = models.CharField(
        max_length=100,
        blank= True
    )

    role= models.CharField(
        max_length=20,
        choices= Role.choices,
        default=Role.EMPLOYEE,
        help_text=(   ##legacy field kept in sync with `roles`; do not use for authorization
            "Legacy single-role field kept for backward "
            "compatibility. Authorization uses `roles`."
        ),
    )

    ##Explicitly assigned roles: the source of truth for authorization.
    roles = models.ManyToManyField(
        "Role",   ##string ref: the nested Role choices class shadows the model name here
        blank=True,
        related_name="users",
    )

    manager = models.ForeignKey(        ##The manager field points back to another User
        "self",                          ##"self" means the relationship points to the same model.
        on_delete=models.SET_NULL,  ##If the manager's user account is deleted, Django will not delete the employee.
        null=True,   ##Allows the database to store NULL, This is useful because some users may not have a manager.
        blank=True,   ##So you can create a user without selecting a manager.
        related_name="team_members"   ##Defines how you access the employees who report to a particular manager.
    )

    def has_role(self, role_name):
        """
        Return True when `role_name` (a Role.Name value) has been
        explicitly assigned to this user.

        This is the ONLY method permission checks should use.
        ADMIN membership grants no other role implicitly.
        """
        return self.roles.filter(name=role_name).exists()

    def has_any_role(self, *role_names):
        """
        Return True when at least one of the given roles has been
        explicitly assigned to this user.
        """
        return self.roles.filter(name__in=role_names).exists()

    def get_role_names(self):
        """
        Return the list of explicitly assigned role names.
        """
        return list(
            self.roles.filter(is_active=True)
            .values_list("name", flat=True)
        )

    def save(self, *args, **kwargs):
        ##Auto-generate the employee ID only for new users
        ##when it was left blank. Existing IDs (system- or
        ##manually-assigned) are never overwritten.
        if (
            not self.pk
            and not (self.employee_id or "").strip()
        ):
            from .services import generate_employee_id

            self.employee_id = generate_employee_id()

        super().save(*args, **kwargs)

    def __str__(self):     ##This method controls how a User object is displayed as text in Django Admin, shell, forms, etc
        return f"{self.employee_id} - {self.get_full_name()}"  ##Gets the employee ID of the current user. and returns the full name
