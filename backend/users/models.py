from django.db import models

from django.contrib.auth.models import AbstractUser  ##imports Django's built-in base class for creating a custom user model.

# Create your models here.

class User(AbstractUser):

    class Role(models.TextChoices):  ##is used to create a fixed set of choices for a model field.
        EMPLOYEE = "EMPLOYEE", "Employee"   ##"EMPLOYEE"     → value stored in the database
        REVIEWER = "REVIEWER", "Reviewer"   ## "Employee"     → human-readable name shown in forms/adm
        MANAGER = "MANAGER", "Manager"
        ADMIN = "ADMIN", "Admin"

    employee_id= models.CharField(
        max_length=20,
        unique=True
    )

    department = models.CharField(
        max_length=100,
        blank= True
    )

    role= models.CharField(
        max_length=20,
        choices= Role.choices,
        default=Role.EMPLOYEE
    )

    manager = models.ForeignKey(        ##The manager field points back to another User
        "self",                          ##"self" means the relationship points to the same model.
        on_delete=models.SET_NULL,  ##If the manager's user account is deleted, Django will not delete the employee.
        null=True,   ##Allows the database to store NULL, This is useful because some users may not have a manager.
        blank=True,   ##So you can create a user without selecting a manager.
        related_name="team_members"   ##Defines how you access the employees who report to a particular manager.
    )

    def __str__(self):     ##This method controls how a User object is displayed as text in Django Admin, shell, forms, etc
        return f"{self.employee_id} - {self.get_full_name()}"  ##Gets the employee ID of the current user. and returns the full name
