import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import IntegrityError
from recipes.models import Tag


class Command(BaseCommand):
    help = 'Import tags from a JSON file'

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
                name = entry.get('name', '').strip()
                slug = entry.get('slug', '').strip()

                if not name or not slug:
                    self.stdout.write(
                        self.style.ERROR(f'Invalid entry: {entry}'))
                    continue

                try:
                    Tag.objects.get_or_create(
                        name=name,
                        slug=slug
                    )
                except IntegrityError as error:
                    self.stdout.write(self.style.ERROR(
                        f'Error importing tag "{name}": {error}'))

        self.stdout.write(self.style.SUCCESS(
            f'Importing data from "{filename}" completed successfully'))
