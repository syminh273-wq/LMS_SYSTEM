from rest_framework.response import Response
from rest_framework.views import APIView

from features.portfolio.services.portfolio_service import PortfolioService


class StudentProfileSettingsView(APIView):
    """
    Get (GET) or update (PATCH) the current student's own profile settings.
    @return: profile settings
    """

    def get(self, request):
        svc = PortfolioService()
        return Response(svc.get_profile_settings(request.user))

    def patch(self, request):
        svc = PortfolioService()
        return Response(svc.update_profile_settings(request.user, request.data))


class PublicStudentProfileView(APIView):
    """
    Get a student's public profile.
    @param consumer_uid: the student to look up
    @return: public profile settings + consumer/space summary
    """

    def get(self, request, consumer_uid=None):
        svc = PortfolioService()
        data = svc.get_public_profile_bundle(consumer_uid)

        visibility = data.get('profile_visibility', 'public')
        is_owner = str(getattr(request.user, 'uid', '')) == str(consumer_uid)

        if not is_owner and visibility == 'private':
            return Response({'error': 'Profile này ở chế độ riêng tư.'}, status=403)

        return Response(data)
