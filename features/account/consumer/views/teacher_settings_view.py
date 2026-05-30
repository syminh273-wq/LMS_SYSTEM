from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from features.account.consumer.services.teacher_settings_service import TeacherSettingsService

class TeacherSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        svc = TeacherSettingsService()
        settings = svc.get_all(request.user.uid)
        return Response(settings)

    def patch(self, request):
        svc = TeacherSettingsService()
        settings = svc.update_bulk(request.user.uid, request.data)
        return Response(settings)
