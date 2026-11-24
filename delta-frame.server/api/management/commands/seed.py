from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import CameraAngle, Tool, User

ADMIN_EMAIL = "bohdan.dev777@gmail.com"

SAMPLE_USERS = [
    {
        "username": "inspector",
        "email": "inspector@deltaframe.local",
        "password": "inspector123",
        "role": "INSPECTOR",
        "first_name": "Alex",
        "last_name": "Inspector",
    },
    {
        "username": "worker",
        "email": "worker@deltaframe.local",
        "password": "worker123",
        "role": "WORKER",
        "first_name": "Sam",
        "last_name": "Worker",
    },
]

SAMPLE_TOOLS = [
    {
        "name": "Digital Torque Wrench 1/2\"",
        "description": "Precision digital torque wrench for calibrated assembly checks.",
        "status": "AVAILABLE",
        "angles": [
            {
                "name": "Front",
                "target_distance_cm": 25.0,
                "target_lux": 400,
                "tolerance_margin_cm": 2.5,
            },
            {
                "name": "Back",
                "target_distance_cm": 25.0,
                "target_lux": 400,
                "tolerance_margin_cm": 2.5,
            },
            {
                "name": "Head Close-Up",
                "target_distance_cm": 15.0,
                "target_lux": 550,
                "tolerance_margin_cm": 1.5,
            },
        ],
    },
    {
        "name": "Cordless Rotary Hammer Drill",
        "description": "Heavy-duty SDS-Plus rotary hammer drill for concrete anchoring.",
        "status": "AVAILABLE",
        "angles": [
            {
                "name": "Front",
                "target_distance_cm": 30.0,
                "target_lux": 450,
                "tolerance_margin_cm": 3.0,
            },
            {
                "name": "Left Side",
                "target_distance_cm": 35.0,
                "target_lux": 420,
                "tolerance_margin_cm": 3.0,
            },
            {
                "name": "Chuck Detail",
                "target_distance_cm": 18.0,
                "target_lux": 600,
                "tolerance_margin_cm": 2.0,
            },
        ],
    },
]


class Command(BaseCommand):
    help = "Seed initial users, superuser role, sample tools, and camera angles."

    @transaction.atomic
    def handle(self, *args, **options):
        self._promote_superuser()
        self._seed_users()
        self._seed_tools()
        self.stdout.write(self.style.SUCCESS("Database seeding completed."))

    def _promote_superuser(self) -> None:
        updated = User.objects.filter(
            email=ADMIN_EMAIL,
            is_superuser=True,
        ).update(role="ADMIN")

        if updated:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Set role='ADMIN' for superuser '{ADMIN_EMAIL}'."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"No superuser found with email '{ADMIN_EMAIL}'. Skipping role update."
                )
            )

    def _seed_users(self) -> None:
        for user_data in SAMPLE_USERS:
            user, created = User.objects.get_or_create(
                username=user_data["username"],
                defaults={
                    "email": user_data["email"],
                    "role": user_data["role"],
                    "first_name": user_data["first_name"],
                    "last_name": user_data["last_name"],
                },
            )
            if created:
                user.set_password(user_data["password"])
                user.save(update_fields=["password"])
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created {user.role} user '{user.username}' ({user.email})."
                    )
                )
            else:
                self.stdout.write(
                    f"User '{user.username}' already exists ({user.role})."
                )

    def _seed_tools(self) -> None:
        for tool_data in SAMPLE_TOOLS:
            tool, created = Tool.objects.get_or_create(
                name=tool_data["name"],
                defaults={
                    "description": tool_data["description"],
                    "status": tool_data["status"],
                },
            )
            action = "Created" if created else "Found existing"
            self.stdout.write(f"{action} tool: {tool}")

            for angle_data in tool_data["angles"]:
                angle, angle_created = CameraAngle.objects.get_or_create(
                    tool=tool,
                    name=angle_data["name"],
                    defaults={
                        "target_distance_cm": angle_data["target_distance_cm"],
                        "target_lux": angle_data["target_lux"],
                        "tolerance_margin_cm": angle_data["tolerance_margin_cm"],
                    },
                )
                if angle_created:
                    self.stdout.write(
                        f"  + Added angle '{angle.name}' "
                        f"({angle.target_distance_cm} cm, {angle.target_lux} lux, "
                        f"±{angle.tolerance_margin_cm} cm)"
                    )
