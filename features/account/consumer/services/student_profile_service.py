import json
import uuid
from datetime import datetime

from features.account.consumer.models.student_profile_settings import StudentProfileSettings


class StudentProfileService:

    def get_or_create(self, consumer_uid) -> StudentProfileSettings:
        uid = uuid.UUID(str(consumer_uid))
        try:
            return StudentProfileSettings.objects.get(consumer_uid=uid)
        except StudentProfileSettings.DoesNotExist:
            return StudentProfileSettings.create(consumer_uid=uid)

    def update(self, consumer_uid, data: dict) -> StudentProfileSettings:
        settings = self.get_or_create(consumer_uid)
        allowed = {
            'bio', 'address', 'city', 'country',
            'theme_color', 'cover_style', 'cover_value',
            'show_stats', 'show_classrooms', 'show_grades', 'show_badges',
            'show_address', 'show_links', 'show_hobbies', 'show_certificates',
            'show_activity', 'show_contact',
            'sections_order', 'profile_visibility', 'metadata',
        }
        update_kwargs = {k: v for k, v in data.items() if k in allowed}

        # Serialize JSON fields
        for field in ('sections_order', 'metadata'):
            if field in update_kwargs and not isinstance(update_kwargs[field], str):
                update_kwargs[field] = json.dumps(update_kwargs[field], ensure_ascii=False)

        update_kwargs['updated_at'] = datetime.utcnow()
        for k, v in update_kwargs.items():
            setattr(settings, k, v)
        settings.save()
        return settings

    def serialize(self, settings: StudentProfileSettings) -> dict:
        def _json(val):
            if not val:
                return None
            try:
                return json.loads(val)
            except Exception:
                return val

        return {
            'consumer_uid':      str(settings.consumer_uid),
            'bio':               settings.bio or '',
            'address':           settings.address or '',
            'city':              settings.city or '',
            'country':           settings.country or 'Việt Nam',
            'theme_color':       settings.theme_color or 'indigo',
            'cover_style':       settings.cover_style or 'gradient',
            'cover_value':       settings.cover_value or '',
            'show_stats':        bool(settings.show_stats),
            'show_classrooms':   bool(settings.show_classrooms),
            'show_grades':       bool(settings.show_grades),
            'show_badges':       bool(settings.show_badges),
            'show_address':      bool(settings.show_address),
            'show_links':        bool(settings.show_links),
            'show_hobbies':      bool(settings.show_hobbies),
            'show_certificates': bool(settings.show_certificates),
            'show_activity':     bool(settings.show_activity),
            'show_contact':      bool(settings.show_contact),
            'sections_order':    _json(settings.sections_order) or ['classrooms', 'grades', 'certificates', 'about'],
            'profile_visibility': settings.profile_visibility or 'class_only',
            'metadata':          _json(settings.metadata) or {},
            'updated_at':        settings.updated_at.isoformat() if settings.updated_at else None,
        }
