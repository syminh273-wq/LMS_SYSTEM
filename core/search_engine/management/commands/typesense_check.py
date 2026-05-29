from django.core.management.base import BaseCommand

from core.search_engine.typesense.client import TypesenseClient
from core.search_engine.typesense.schemas import TypesenseSchema


class Command(BaseCommand):
    help = 'Check Typesense health and collection status.'

    def add_arguments(self, parser):
        parser.add_argument('--health',     action='store_true')
        parser.add_argument('--stats',      action='store_true')
        parser.add_argument('--collection', type=str, default='')

    def handle(self, *args, **options):
        client = TypesenseClient()

        # ── Health ─────────────────────────────────────────────────────────
        healthy = client.health()
        icon = '✓' if healthy else '✗'
        style = self.style.SUCCESS if healthy else self.style.ERROR
        self.stdout.write(style(f'{icon}  Typesense health: {"OK" if healthy else "UNREACHABLE"}'))

        if options['health']:
            return

        # ── Collections ────────────────────────────────────────────────────
        names = [options['collection']] if options['collection'] else TypesenseSchema.names()
        self.stdout.write('')
        for name in names:
            try:
                info = client.get_collection(name)
                count = info.get('num_documents', '?')
                self.stdout.write(self.style.SUCCESS(f'  ✓  {name}  ({count} docs)'))
                if options['stats']:
                    self.stdout.write(f'       fields: {[f["name"] for f in info.get("fields", [])]}')
            except Exception:
                self.stdout.write(self.style.ERROR(f'  ✗  {name}  (not found)'))
