import logging

logger = logging.getLogger('view_logging')


class ViewLoggingMiddleware:
    """Logs which ViewSet/View class and action handles every request.

    process_view runs after Django resolves the URL, so view_func already
    carries the DRF ViewSet metadata (`.cls`, `.actions`) needed to name
    the exact handler — that info isn't available in __call__.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        view_class = getattr(view_func, 'cls', None) or getattr(view_func, 'view_class', None)
        class_name = view_class.__name__ if view_class else view_func.__name__

        actions = getattr(view_func, 'actions', None) or {}
        action_name = actions.get(request.method.lower(), request.method.lower())

        logger.info('[VIEW] %s %s -> %s.%s', request.method, request.path, class_name, action_name)
        return None
