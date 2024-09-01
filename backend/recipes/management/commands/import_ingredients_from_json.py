import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import IntegrityError
from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Import ingredients from a JSON file'

    def add_arguments(self, parser):
        parser.add_argument(
            'filename',
            type=str,
            help='The name of the JSON file to import',
        )

    def handle(self, *args, **options):
        filename = options['filename']
        path = os.path.join(settings.BASE_DIR, 'data/', filename)

        if not os.path.exists(path):
            self.stdout.write(
                self.style.ERROR(f'File "{filename}" does not exist'))
            return

        with open(path, 'r', encoding='utf-8') as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError as e:
                self.stdout.write(
                    self.style.ERROR(f'Error decoding JSON file: {e}'))
                return

            for entry in data:
                ingredient_name = entry.get('name', '').strip()
                measurement_unit = entry.get('measurement_unit', '').strip()

                if not ingredient_name or not measurement_unit:
                    self.stdout.write(
                        self.style.ERROR(f'Invalid entry: {entry}'))
                    continue

                try:
                    Ingredient.objects.get_or_create(
                        name=ingredient_name,
                        measurement_unit=measurement_unit
                    )
                except IntegrityError as error:
                    self.stdout.write(self.style.ERROR(
                        f'Error importing {ingredient_name}: {error}'))

        self.stdout.write(self.style.SUCCESS(
            f'Importing data from "{filename}" completed successfully'))
