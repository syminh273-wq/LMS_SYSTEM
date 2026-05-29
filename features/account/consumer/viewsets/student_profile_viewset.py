from rest_framework.response import Response
from rest_framework.views import APIView

from features.account.consumer.services.student_profile_service import StudentProfileService


class StudentProfileSettingsView(APIView):
    """
    GET  /api/v1/consumer/account/profile-settings/   — own settings
    PATCH /api/v1/consumer/account/profile-settings/  — update own settings
    """

    def get(self, request):
        svc = StudentProfileService()
        settings = svc.get_or_create(request.user.uid)
        return Response(svc.serialize(settings))

    def patch(self, request):
        svc = StudentProfileService()
        settings = svc.update(request.user.uid, request.data)
        return Response(svc.serialize(settings))


class PublicStudentProfileView(APIView):
    """
    GET /api/v1/consumer/account/profile/<consumer_uid>/public/
    Visible to: teacher (Space) or same consumer.
    Returns settings + basic consumer info merged.
    """

    def get(self, request, consumer_uid=None):
        from features.account.consumer.services import ConsumerService
        from features.account.consumer.serializers import ConsumerAccountSerializer
        from features.account.space.models.space import Space

        svc = StudentProfileService()
        settings = svc.get_or_create(consumer_uid)
        data = svc.serialize(settings)

        visibility = data['profile_visibility']
        is_owner   = str(getattr(request.user, 'uid', '')) == str(consumer_uid)
        is_teacher = isinstance(request.user, Space)

        if not is_owner and visibility == 'private':
            return Response({'error': 'Profile này ở chế độ riêng tư.'}, status=403)

        # Fetch consumer basic info
        try:
            consumer = ConsumerService().find(consumer_uid)
            data['consumer'] = ConsumerAccountSerializer(consumer).data
        except Exception:
            data['consumer'] = None

        return Response(data)
