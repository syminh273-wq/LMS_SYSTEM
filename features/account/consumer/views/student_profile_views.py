from rest_framework.response import Response
from rest_framework.views import APIView

from features.portfolio.services.portfolio_service import PortfolioService


def _build_space_profile_dict(space) -> dict:
    from core.storages.storage_service import storage_service
    avatar_raw = space.avatar_url or space.logo_url or ''
    avatar = storage_service.get_public_url(avatar_raw) if avatar_raw else ''
    full_name = space.full_name or space.name or ''
    return {
        'uid': str(space.uid),
        'pid': getattr(space, 'pid', '') or '',
        'username': space.name or space.slug or '',
        'email': space.email or '',
        'first_name': '',
        'last_name': '',
        'full_name': full_name,
        'phone': '',
        'avatar_url': avatar,
        'is_active': bool(getattr(space, 'is_active', True)),
        'created_at': space.created_at.isoformat() if getattr(space, 'created_at', None) else '',
        'updated_at': space.updated_at.isoformat() if getattr(space, 'updated_at', None) else '',
    }


def _format_address_public(addr_dict: dict) -> str:
    if not addr_dict:
        return ''
    parts = []
    for key in ('line1', 'ward_name', 'province_name'):
        value = (addr_dict.get(key) or '').strip()
        if value:
            parts.append(value)
    return ', '.join(parts)


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
        from features.account.consumer.services import ConsumerService
        from features.account.consumer.serializers import ConsumerAccountSerializer
        from features.account.consumer.services.address_service import AddressService
        from features.account.space.models.space import Space
        from features.portfolio.services.portfolio_service import PortfolioService
        import uuid as _uuid

        svc = PortfolioService()
        data = svc.get_profile_settings_or_public(consumer_uid)

        visibility = data.get('profile_visibility', 'public')
        is_owner   = str(getattr(request.user, 'uid', '')) == str(consumer_uid)
        is_teacher = isinstance(request.user, Space)

        if not is_owner and visibility == 'private':
            return Response({'error': 'Profile này ở chế độ riêng tư.'}, status=403)

        owner_type = None
        consumer_dict = None
        try:
            consumer = ConsumerService().find(consumer_uid)
            consumer_dict = ConsumerAccountSerializer(consumer).data
            owner_type = 'consumer'
        except Exception:
            consumer_dict = None

        space_instance = None
        if not consumer_dict:
            try:
                space_rows = list(Space.objects.filter(uid=_uuid.UUID(str(consumer_uid))).limit(1))
                if space_rows:
                    space_instance = space_rows[0]
                    consumer_dict = _build_space_profile_dict(space_instance)
                    owner_type = 'space'
            except Exception:
                consumer_dict = None

        if data.get('show_address') and owner_type:
            try:
                addr_dict = AddressService().get_for_owner(consumer_uid, owner_type)
                data['address'] = _format_address_public(addr_dict or {})
            except Exception:
                data['address'] = ''
        else:
            data['address'] = ''

        data['consumer'] = consumer_dict
        return Response(data)
