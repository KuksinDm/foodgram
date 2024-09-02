from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Create 5 regular users with hardcoded credentials'

    def handle(self, *args, **options):
        users_data = [
            {
                'username': 'testuserone', 'email': 'user1@example.com',
                'password': 'testpass', 'first_name': 'Иван',
                'last_name': 'Иванов'
            },
            {
                'username': 'testusertwo', 'email': 'user2@example.com',
                'password': 'testpass', 'first_name': 'Мария',
                'last_name': 'Петрова'
            },
            {
                'username': 'testuserthree', 'email': 'user3@example.com',
                'password': 'testpass', 'first_name': 'Олег',
                'last_name': 'Сидоров'
            },
            {
                'username': 'testuserfour', 'email': 'user4@example.com',
                'password': 'testpass', 'first_name': 'Анна',
                'last_name': 'Кузнецова'
            },
            {
                'username': 'testuserfive', 'email': 'user5@example.com',
                'password': 'testpass', 'first_name': 'Дмитрий',
                'last_name': 'Смирнов'
            }
        ]

        for user_data in users_data:
            if User.objects.filter(username=user_data['username']).exists():
                self.stdout.write(self.style.WARNING(
                    f'User with username {user_data["username"]} already '
                    f'exists.'))
            else:
                User.objects.create_user(
                    username=user_data['username'],
                    email=user_data['email'],
                    password=user_data['password'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name']
                )
                self.stdout.write(self.style.SUCCESS(
                    f'User {user_data["username"]} created successfully.'))
