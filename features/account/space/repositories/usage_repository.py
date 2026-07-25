from datetime import datetime

from features.account.space.models.api_usage import ApiUsage
from features.resource.models.resource import Resource


class UsageRepository:
    def get_total_storage_bytes(self, space_id):
        """Sum of all non-deleted resource file sizes owned by this space."""
        resources = Resource.objects.filter(
            bucket=0,
            owner_id=space_id,
            is_deleted=False,
        )
        total = sum(r.size or 0 for r in resources)
        return total

    def get_api_calls_this_month(self, space_id):
        """Get the counter value for current month."""
        year_month = datetime.now().strftime('%Y-%m')
        try:
            record = ApiUsage.objects.get(
                space_id=space_id,
                year_month=year_month,
            )
            return record.call_count or 0
        except ApiUsage.DoesNotExist:
            return 0

    def increment_api_calls(self, space_id):
        """Increment the API call counter for current month."""
        year_month = datetime.now().strftime('%Y-%m')
        ApiUsage.objects(
            space_id=space_id,
            year_month=year_month,
        ).update(call_count__increment=1)

    def get_active_classrooms_count(self, teacher_id):
        """Count active classrooms for a teacher."""
        from features.course.classroom.models import Classroom
        classrooms = Classroom.objects.filter(
            teacher_id=teacher_id,
            is_deleted=False,
            status='active',
        )
        return len(list(classrooms))
