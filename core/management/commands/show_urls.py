from django.core.management.base import BaseCommand
from django.urls import get_resolver
from django.conf import settings

class Command(BaseCommand):
    help = 'Show all URLs in the project grouped by modules'

    def handle(self, *args, **options):
        urlconf = settings.ROOT_URLCONF
        resolver = get_resolver(urlconf)
        
        self.stdout.write(self.style.SUCCESS("List of all URLs grouped by modules:"))
        
        url_groups = {}
        self.collect_urls(resolver.url_patterns, '', url_groups)

        for group_name, urls in sorted(url_groups.items()):
            self.stdout.write(f"\n{self.style.MIGRATE_HEADING(f'--- Module: {group_name} ---')}")
            for path, view_name in urls:
                # Highlight API endpoints
                if path.startswith('api/'):
                    styled_path = self.style.SQL_FIELD(path)
                    styled_view = self.style.SUCCESS(f"({view_name})")
                else:
                    styled_path = self.style.NOTICE(path)
                    styled_view = self.style.HTTP_INFO(f"({view_name})")

                self.stdout.write(f"  {styled_path} {styled_view}")

    def collect_urls(self, patterns, prefix, url_groups):
        for pattern in patterns:
            if hasattr(pattern, 'url_patterns'):
                new_prefix = prefix + str(pattern.pattern)
                self.collect_urls(pattern.url_patterns, new_prefix, url_groups)
            else:
                path = prefix + str(pattern.pattern)
                callback = getattr(pattern, 'callback', None)
                view_name = "Unknown"
                
                if callback:
                    if hasattr(callback, 'view_class'):
                        view_name = callback.view_class.__name__
                    elif hasattr(callback, '__name__'):
                        view_name = callback.__name__
                    elif hasattr(callback, '__class__'):
                        view_name = callback.__class__.__name__

                # Determine group
                if path.startswith('api/'):
                    parts = path.split('/')
                    if len(parts) >= 3:
                        group = "/".join(parts[:3]) # e.g. api/v1/consumer
                    else:
                        group = "api"
                elif path.startswith('admin/'):
                    group = "admin"
                else:
                    group = "other"

                if group not in url_groups:
                    url_groups[group] = []
                url_groups[group].append((path, view_name))
