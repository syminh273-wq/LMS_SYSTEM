from features.account.space.models import Space


class SpaceApiTrackingMiddleware:
    """Counts API requests made by authenticated Space accounts.

    Increments a Cassandra counter per Space per month. Runs after
    authentication middleware so request.user is available.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if not hasattr(request, 'user') or not request.user:
            return response

        if not getattr(request.user, 'is_authenticated', False):
            return response

        if not isinstance(request.user, Space):
            return response

        try:
            from features.account.space.services.usage_service import UsageService
            usage_service = UsageService()
            usage_service.increment_api_calls(request.user.uid)
        except Exception:
            pass

        return response
