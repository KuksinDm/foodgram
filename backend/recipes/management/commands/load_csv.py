import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import IntegrityError
from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Import ingredients from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            'filename',
            type=str,
            help='The name of the CSV file to import',
        )

    def handle(self, *args, **options):
        filename = options['filename']
        path = os.path.join(settings.BASE_DIR, 'data/', filename)

        if not os.path.exists(path):
            self.stdout.write(
                self.style.ERROR(f'File "{filename}" does not exist'))
            return

        with open(path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                if len(row) < 2:
                    self.stdout.write(
                        self.style.ERROR(f'Invalid row format: {row}'))
                    continue

                ingredient_name = row[0].strip()
                measurement_unit = row[1].strip()

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
