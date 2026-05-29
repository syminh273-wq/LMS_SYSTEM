from importlib import import_module

from django.core.management.base import BaseCommand, CommandError

from core.search_engine.typesense.indexer import LMSIndexer
from core.search_engine.typesense.service import TypesenseService


_BACKFILL_CONFIG = {
    'lms_classroom': {
        'module': 'features.course.classroom.models',
        'model':  'Classroom',
        'bucket_field': 'bucket',
    },
    'lms_exam': {
        'module': 'features.course.exam.models',
        'model':  'Exam',
        'bucket_field': 'bucket',
    },
    'lms_consumer': {
        'module': 'features.account.consumer.models',
        'model':  'Consumer',
        'bucket_field': None,
    },
    'lms_space': {
        'module': 'features.account.space.models',
        'model':  'Space',
        'bucket_field': None,
    },
    'lms_quiz': {
        'module': 'features.quiz.models',
        'model':  'Quiz',
        'bucket_field': 'bucket',
    },
}


class Command(BaseCommand):
    help = (
        'Backfill a Typesense collection with existing database records.\n'
        'Usage: python manage.py typesense_backfill <collection> [--batch-size 500]'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'collection', nargs='?', default='',
            help='Collection to backfill (default: all).',
        )
        parser.add_argument('--batch-size', type=int, default=500)
        parser.add_argument('--limit', type=int, default=0, help='Max records (0 = all).')

    def handle(self, *args, **options):
        svc = TypesenseService()
        col = options['collection']
        targets = [col] if col else list(_BACKFILL_CONFIG.keys())

        for collection_name in targets:
            cfg = _BACKFILL_CONFIG.get(collection_name)
            if not cfg:
                raise CommandError(f'Unknown collection: {collection_name}')

            self.stdout.write(f'\n▶  Backfilling "{collection_name}" …')
            module = import_module(cfg['module'])
            Model = getattr(module, cfg['model'])
            transformer = LMSIndexer.BACKFILL_MAP[collection_name][2]

            # Fetch all records — Cassandra models with bucket=0
            try:
                if cfg['bucket_field']:
                    qs = list(Model.objects.filter(**{cfg['bucket_field']: 0}).all())
                else:
                    qs = list(Model.objects.all())
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗  Failed to fetch: {e}'))
                continue

            if options['limit']:
                qs = qs[:options['limit']]

            result = svc.bulk_upsert(
                collection_name,
                qs,
                transformer,
                batch_size=options['batch_size'],
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'  ✓  {result["ok"]} indexed, {result["failed"]} failed '
                    f'(total {result["total"]})'
                )
            )
