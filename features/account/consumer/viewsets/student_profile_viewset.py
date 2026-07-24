from rest_framework.response import Response
from rest_framework.views import APIView

from features.account.consumer.services.student_profile_service import StudentProfileService


def _build_space_profile_dict(space) -> dict:
    """Build a Consumer-shaped profile dict from a Space instance so the
    frontend (which expects a Consumer) can render name/avatar without changes."""
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
    """Format an address dict into a single human-readable string for public display.

    Order: line1, ward_name, province_name. line2 is omitted to keep the header compact
    (matches the frontend ProfileHeaderInfo.formatAddress contract).
    """
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

    Returns the StudentProfileSettings for the given uid, plus a `consumer`
    field with basic info. The target may be either a Consumer (student) or
    a Space (teacher); for Space we synthesize a Consumer-shaped dict so
    the frontend profile page can render name/avatar uniformly.
    """

    def get(self, request, consumer_uid=None):
        from features.account.consumer.services import ConsumerService
        from features.account.consumer.serializers import ConsumerAccountSerializer
        from features.account.consumer.services.address_service import AddressService
        from features.account.space.models.space import Space
        import uuid as _uuid

        svc = StudentProfileService()
        settings = svc.get_or_create(consumer_uid)
        data = svc.serialize(settings)

        visibility = data.get('profile_visibility', 'public')
        is_owner   = str(getattr(request.user, 'uid', '')) == str(consumer_uid)
        is_teacher = isinstance(request.user, Space)

        if not is_owner and visibility == 'private':
            return Response({'error': 'Profile này ở chế độ riêng tư.'}, status=403)

        # Determine owner_type by probing Consumer first, then Space.
        owner_type = None
        consumer_dict = None
        try:
            consumer = ConsumerService().find(consumer_uid)
            consumer_dict = ConsumerAccountSerializer(consumer).data
            owner_type = 'consumer'
        except Exception:
            consumer_dict = None

        # Fallback: try to find as Space (teacher) and build a compatible dict
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

        # If the owner allows showing address, synthesize a formatted string
        # from the live Address row so non-owners see the same value the owner
        # sees in their AddressSection. The settings.address column is not
        # maintained on write (the Address table is the source of truth), so
        # we must join here rather than reading it from the settings row.
        # owner_type must be probed first because the address row's owner_type
        # is 'space' for teachers and 'consumer' for students.
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
