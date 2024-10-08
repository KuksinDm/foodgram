import os
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a superuser with credentials from environment variables'

    def handle(self, *args, **options):
        username = os.getenv('SUPERUSER_USERNAME', 'admin')
        email = os.getenv('SUPERUSER_EMAIL', 'admin@example.com')
        password = os.getenv('SUPERUSER_PASSWORD', 'adminpassword')
        first_name = os.getenv('SUPERUSER_FIRST_NAME', 'Admin')
        last_name = os.getenv('SUPERUSER_LAST_NAME', 'User')

        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(
                    f'Superuser with username {username} already exists.'))
        else:
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'Superuser {username} created successfully.'))
