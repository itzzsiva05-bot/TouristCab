from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Creates/updates the default admin login (Admin@gmail.com / Admin123)."

    def add_arguments(self, parser):
        parser.add_argument("--email", default="Admin@gmail.com")
        parser.add_argument("--password", default="Admin123")

    def handle(self, *args, **options):
        email = options["email"]
        password = options["password"]

        user, created = User.objects.get_or_create(
            username=email,
            defaults={"email": email, "is_staff": True, "is_superuser": True},
        )
        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} admin login: {email} / {password}"))
