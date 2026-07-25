from features.account.space.repositories.usage_repository import UsageRepository

PLAN_QUOTAS = {
    'free': {
        'storage_limit_bytes': 1 * 1024 * 1024 * 1024,       # 1 GB
        'api_calls_limit': 10_000,
    },
    'pro': {
        'storage_limit_bytes': 10 * 1024 * 1024 * 1024,      # 10 GB
        'api_calls_limit': 100_000,
    },
    'enterprise': {
        'storage_limit_bytes': 100 * 1024 * 1024 * 1024,     # 100 GB
        'api_calls_limit': 1_000_000,
    },
}


class UsageService:
    def __init__(self):
        self.repository = UsageRepository()

    def get_usage(self, space):
        plan = getattr(space, 'plan', None) or 'free'
        quota = PLAN_QUOTAS.get(plan, PLAN_QUOTAS['free'])

        storage_used = self.repository.get_total_storage_bytes(space.uid)
        storage_limit = quota['storage_limit_bytes']

        api_calls = self.repository.get_api_calls_this_month(space.uid)
        api_calls_limit = quota['api_calls_limit']

        active_classrooms = self.repository.get_active_classrooms_count(space.uid)

        return {
            'storage_used_bytes': storage_used,
            'storage_limit_bytes': storage_limit,
            'storage_used_percent': round((storage_used / storage_limit) * 100, 1) if storage_limit else 0,
            'api_calls_this_month': api_calls,
            'api_calls_limit': api_calls_limit,
            'api_calls_percent': round((api_calls / api_calls_limit) * 100, 1) if api_calls_limit else 0,
            'active_classrooms': active_classrooms,
            'plan': plan,
        }

    def increment_api_calls(self, space_id):
        self.repository.increment_api_calls(space_id)
