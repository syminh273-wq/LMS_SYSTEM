"""
Create a new LMS app under `features/<module>/<app>/` from a scaffold template.

Usage:
    python manage.py startapp_scaffold features.course.exam
    python manage.py startapp_scaffold features.calendar_event
    python manage.py startapp_scaffold features.course.exam --target-dir features/course

App name format:
    features.<module>.<app>   -> creates features/<module>/<app>/
    features.<app>            -> creates features/<app>/
    <app>                     -> creates <app>/ in --target-dir (default: project root)

Scaffold follows the LMS layered pattern documented in AGENTS.md:
    apps.py + models/ + repositories/ + services/ + serializers/ +
    viewsets/ + routing/urls.py
"""
import os
import re
import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.utils.str import to_pascal_case, to_plural_snake_case, to_snake_case


class Command(BaseCommand):
    help = "Create a new LMS app under features/ from the project scaffold template."

    def add_arguments(self, parser):
        parser.add_argument(
            'app_name',
            type=str,
            help='App name (e.g. features.course.exam, features.calendar_event, or myapp).',
        )
        parser.add_argument(
            '--target-dir',
            type=str,
            default=None,
            help='Target directory to create the app (defaults to project root).',
        )

    def handle(self, *args, **options):
        app_name = options['app_name'].strip().strip('/')
        target_dir = Path(options.get('target_dir') or settings.BASE_DIR).resolve()

        scaffold_path = Path(settings.BASE_DIR) / 'templates' / 'scaffold' / 'dummy'
        if not scaffold_path.exists():
            raise CommandError(
                f'Scaffold template not found at "{scaffold_path}".'
            )

        full_app_name, app_path, app_module_name, master_module_name = self._resolve_paths(
            app_name, target_dir
        )

        if app_path.exists():
            raise CommandError(f'App directory "{app_path}" already exists.')

        snake_case_name = to_snake_case(app_module_name)
        class_name = to_pascal_case(app_module_name)
        upper_snake_case = snake_case_name.upper()
        plural_snake_case = to_plural_snake_case(snake_case_name)

        # Table name: <module>_<app>s for nested apps, just <app>s for
        # top-level apps under `features/`. The `features_` prefix is
        # never wanted (the LMS convention uses the app/module own name).
        is_nested_under_features = (
            master_module_name != app_module_name
            and master_module_name != 'features'
        )
        if is_nested_under_features:
            table_name = f'{to_snake_case(master_module_name)}_{plural_snake_case}'
        else:
            table_name = plural_snake_case

        self.stdout.write(
            f'Creating app "{app_module_name}" (full path: "{full_app_name}") '
            f'at "{app_path}"...'
        )

        try:
            self._copy_scaffold_structure(
                scaffold_path=scaffold_path,
                target_path=app_path,
                app_name=app_module_name,
                snake_case_name=snake_case_name,
                class_name=class_name,
                upper_snake_case=upper_snake_case,
                plural_snake_case=plural_snake_case,
                table_name=table_name,
                full_app_name=full_app_name,
            )

            if app_module_name != master_module_name:
                master_path = app_path.parent
                master_init = master_path / '__init__.py'
                if not master_init.exists():
                    master_init.touch()
                    self.stdout.write(f'Created {master_init}')

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created app "{app_module_name}" at "{app_path}"'
                )
            )
            self._print_next_steps(
                app_name=app_name,
                full_app_name=full_app_name,
                app_path=app_path,
                table_name=table_name,
                plural_snake_case=plural_snake_case,
            )

        except Exception as exc:
            if app_path.exists():
                shutil.rmtree(app_path)
            raise CommandError(f'Error creating app: {exc}') from exc

    def _resolve_paths(self, app_name: str, target_dir: Path):
        """Resolve app_name into (full dotted path, on-disk path, app module, master module)."""
        if '.' in app_name:
            parts = app_name.split('.')
            if len(parts) == 2:
                master, sub = parts
                app_path = target_dir / master / sub
                return app_name, app_path, sub, master
            if len(parts) == 3 and parts[0] == 'features':
                master, sub = parts[1], parts[2]
                app_path = target_dir / 'features' / master / sub
                return app_name, app_path, sub, master
            raise CommandError(
                f'Invalid app name "{app_name}". '
                f'Use "features.<module>.<app>", "<module>.<app>", or "<app>".'
            )

        app_path = target_dir / app_name
        return app_name, app_path, app_name, app_name

    def _copy_scaffold_structure(
        self,
        scaffold_path: Path,
        target_path: Path,
        app_name: str,
        snake_case_name: str,
        class_name: str,
        upper_snake_case: str,
        plural_snake_case: str,
        table_name: str,
        full_app_name: str,
    ):
        for root, _dirs, files in os.walk(scaffold_path):
            rel = Path(root).relative_to(scaffold_path)
            dest_dir = target_path / rel
            dest_dir.mkdir(parents=True, exist_ok=True)

            for file in files:
                src = Path(root) / file
                dest_filename = self._process_filename(file, snake_case_name)
                dest = dest_dir / dest_filename
                self._process_file(
                    src,
                    dest,
                    snake_case_name=snake_case_name,
                    class_name=class_name,
                    upper_snake_case=upper_snake_case,
                    plural_snake_case=plural_snake_case,
                    table_name=table_name,
                    full_app_name=full_app_name,
                )

    def _process_filename(self, filename: str, snake_case_name: str) -> str:
        if filename.endswith('.tpl'):
            filename = filename[:-4]
        filename = filename.replace('dummy', snake_case_name)
        return filename

    def _process_file(
        self,
        source: Path,
        dest: Path,
        snake_case_name: str,
        class_name: str,
        upper_snake_case: str,
        plural_snake_case: str,
        table_name: str,
        full_app_name: str,
    ):
        content = source.read_text(encoding='utf-8')
        content = self._replace_content_placeholders(
            content,
            snake_case_name=snake_case_name,
            class_name=class_name,
            upper_snake_case=upper_snake_case,
            plural_snake_case=plural_snake_case,
            table_name=table_name,
            full_app_name=full_app_name,
        )
        dest.write_text(content, encoding='utf-8')

    def _replace_content_placeholders(
        self,
        content: str,
        snake_case_name: str,
        class_name: str,
        upper_snake_case: str,
        plural_snake_case: str,
        table_name: str,
        full_app_name: str,
    ) -> str:
        # 1) Router URL — replaces the `r'dummies'` URL path with the plural.
        #    Done FIRST so step 7 below doesn't see `dummy` inside `dummies`.
        content = re.sub(
            r"router\.register\(r'dummies'",
            f"router.register(r'{plural_snake_case}'",
            content,
        )

        # 2) Dotted package imports/refs to the dummy package — must be
        #    FIRST (after the router URL) so `from dummy.foo import` etc.
        #    become fully-qualified before we touch bare `dummy`.
        content = re.sub(r'from dummy\.', f'from {full_app_name}.', content)
        content = re.sub(r'import dummy\.', f'import {full_app_name}.', content)

        # 3) URL include('dummy.x.y') in routing.
        content = re.sub(
            r"include\(['\"]dummy\.([^'\"]+)['\"]\)",
            rf"include('{full_app_name}.\1')",
            content,
        )

        # 4) Bare `from dummy` / `import dummy` (no trailing dot) for the
        #    package itself. NOT `'<appname>'` strings — those are short
        #    names (basename, label) handled by step 7.
        content = re.sub(r'from dummy(?!\.)', f'from {full_app_name}', content)
        content = re.sub(r'import dummy(?!\.)', f'import {full_app_name}', content)

        # 5) Class-name prefixes without underscore separator: DummyConfig,
        #    DummyViewSet, DummyRequestSerializer → ClassNameConfig, etc.
        #    Plain `Dummy` (no word boundary) is required to catch `DummyConfig`.
        content = content.replace('Dummy', class_name)

        # 6) snake_case identifier prefixes (file/module/var names).
        content = re.sub(r'\bdummy_', f'{snake_case_name}_', content)
        content = re.sub(r'_dummy_', f'_{snake_case_name}_', content)
        content = re.sub(r'\.dummy_', f'.{snake_case_name}_', content)

        # 7) Constants: DUMMY_ -> APP_NAME_ (uppercase).
        content = re.sub(r'\bDUMMY_', f'{upper_snake_case}_', content)

        # 8) Bare `dummy` (NOT followed by `s` + word boundary, to avoid
        #    breaking `dummies` which step 9 handles). No leading `\b`
        #    so that `create_dummy` / `__dummy` / `mydummy` are caught too
        #    (matches the original command's behavior).
        content = re.sub(r'dummy(?!s\b)', snake_case_name, content)

        # 9) Plural `dummies` → plural_snake (e.g. `r'dummies'` already
        #    became `r'exams'` in step 1, but variable names etc. remain).
        content = re.sub(r'\bdummies\b', plural_snake_case, content)

        # 10) Cassandra __table_name__ = '...'.
        content = re.sub(
            r"__table_name__\s*=\s*['\"][^'\"]+['\"]",
            f"__table_name__ = '{table_name}'",
            content,
        )

        # 11) AppConfig.name = '...'. Use lookbehind `(?<!\w)` so the `name`
        #     in `basename='...'` is NOT matched. Only the apps.py template
        #     has such a line.
        content = re.sub(
            r"(?<!\w)name\s*=\s*['\"][^'\"]*['\"]",
            f"name = '{full_app_name}'",
            content,
            count=1,
        )

        return content

    def _print_next_steps(self, app_name, full_app_name, app_path, table_name, plural_snake_case):
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('Next Steps:'))
        self.stdout.write('=' * 60)
        self.stdout.write(
            f'1. Add "{full_app_name}" to INSTALLED_APPS in LMS_SYSTEM/settings.py'
        )
        self.stdout.write(
            f'2. Mount URLs in LMS_SYSTEM/urls.py, e.g.:\n'
            f'     path("api/v1/<scope>/{plural_snake_case}/", include("{full_app_name}.routing.urls")),'
        )
        self.stdout.write(
            f'3. Edit models/{plural_snake_case[:-1] if plural_snake_case.endswith("s") else plural_snake_case}.py '
            f'— add real columns (partition/clustering keys, indexes).'
        )
        self.stdout.write(
            f'4. Register the new model in core/management/commands/lms_sync_cassandra.py, then run:\n'
            f'     python manage.py lms_sync_cassandra\n'
            f'   Table name: {table_name}'
        )
        self.stdout.write(
            '5. Replace placeholder columns in serializers/ and viewsets/ with real business logic.'
        )
        self.stdout.write(f'\nApp created at: {app_path}')
        self.stdout.write('=' * 60)
