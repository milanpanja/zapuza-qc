from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        PLANT_MANAGER = "PM", "Plant Manager"
        QUALITY_ENGINEER = "QE", "Quality Engineer"
        QUALITY_MANAGER = "QM", "Quality Manager"
        SUPERVISOR = "SUP", "Shift Supervisor"
        INSPECTOR = "INS", "QA Floor Inspector"
        OPERATOR = "OPR", "Machine Operator"
        DOCK_CLERK = "DOCK", "Dock Clerk"
        WAREHOUSE = "WH", "Warehouse Clerk"

    role = models.CharField(max_length=5, choices=Role.choices, default=Role.INSPECTOR)
