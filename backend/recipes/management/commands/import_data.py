import csv
import os

from django.conf import settings
from django.contrib.auth.hashers import make_password

from django.core.management.base import BaseCommand
from faker import Faker
from rest_framework.authtoken.models import Token

from recipes.models import Ingredient, Tag
from users.models import User

fake = Faker(['ru_RU', ])

DATA_DIR = os.path.join(settings.BASE_DIR, 'data')


class Command(BaseCommand):
    help = 'Загружаем демо данные'

    def handle(self, *args, **options):

        def create_objects_from_csv(file_path, create_func):
            with open(file_path, 'r') as csv_file:
                reader = csv.reader(csv_file)
                for row in reader:
                    create_func(*row)

        def create_ingredient(name, measurement_unit):
            Ingredient.objects.update_or_create(
                name=name, measurement_unit=measurement_unit)

        def create_tag(name, color, slug):
            Tag.objects.update_or_create(name=name, color=color, slug=slug)

        create_objects_from_csv(
            os.path.join(DATA_DIR, 'ingredients.csv'),
            create_ingredient
        )
        create_objects_from_csv(
            os.path.join(DATA_DIR, 'tags.csv'), create_tag
        )

        if not User.objects.filter(email__startswith='user').exists():
            for i in range(4):
                user, created = User.objects.update_or_create(
                    email=f'user{i}@example.com',
                    defaults={
                        'email': f'user{i}@example.com',
                        'username': f'User{i}',
                        'first_name': fake.first_name_male(),
                        'last_name': fake.last_name_male(),
                        'password': make_password('p@ssw0rd1'),
                    },
                )
                token, created = Token.objects.update_or_create(user=user)
            user_review, created = User.objects.update_or_create(
                email='review@review.com',
                defaults={
                    'email': 'review@review.com',
                    'username': 'review',
                    'first_name': 'Артем',
                    'last_name': 'Нечай',
                    'password': 'reviewadmin1',
                },
            )
            token, created = Token.objects.update_or_create(user=user_review)
        self.stdout.write(self.style.SUCCESS('Данные успешно импортированы.'))
