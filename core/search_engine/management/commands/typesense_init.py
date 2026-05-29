from django.core.management.base import BaseCommand

from core.search_engine.typesense.schemas import TypesenseSchema
from core.search_engine.typesense.client import TypesenseClient


class Command(BaseCommand):
    help = 'Create Typesense collections from registered schemas.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--collections', type=str, default='',
            help='Comma-separated list of collection names to init (default: all).',
        )
        parser.add_argument(
            '--drop', action='store_true',
            help='Drop existing collections before recreating them.',
        )

    def handle(self, *args, **options):
        client = TypesenseClient()
        target = [n.strip() for n in options['collections'].split(',') if n.strip()] \
                 or TypesenseSchema.names()

        for name in target:
            schema = TypesenseSchema.get(name)
            if not schema:
                self.stdout.write(self.style.WARNING(f'  ⚠  No schema for "{name}" — skipped.'))
                continue

            if options['drop']:
                try:
                    client.delete_collection(name)
                    self.stdout.write(f'  🗑  Dropped "{name}"')
                except Exception:
                    pass

            try:
                client.get_collection(name)
                self.stdout.write(self.style.WARNING(f'  –  "{name}" already exists.'))
            except Exception:
                client.create_collection(schema)
                self.stdout.write(self.style.SUCCESS(f'  ✓  Created "{name}"'))
