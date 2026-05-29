from datetime import datetime
from cassandra.cqlengine import columns
from django_cassandra_engine.models import DjangoCassandraModel


class StudentProfileSettings(DjangoCassandraModel):
    """
    Per-student profile customization settings.
    One row per consumer — partition key is consumer_uid.
    metadata stores JSON: hobbies, social_links, certificates, custom_fields.
    """

    consumer_uid = columns.UUID(primary_key=True, required=True)

    # ── Personal info extras ──────────────────────────────────────────────────
    bio             = columns.Text(default='')
    address         = columns.Text(default='')
    city            = columns.Text(default='')
    country         = columns.Text(default='Việt Nam')

    # ── Appearance ────────────────────────────────────────────────────────────
    theme_color     = columns.Text(default='indigo')   # indigo|rose|emerald|amber|violet
    cover_style     = columns.Text(default='gradient') # gradient|solid|mesh
    cover_value     = columns.Text(default='')         # CSS gradient or hex

    # ── Section visibility toggles ────────────────────────────────────────────
    show_stats        = columns.Boolean(default=True)
    show_classrooms   = columns.Boolean(default=True)
    show_grades       = columns.Boolean(default=True)
    show_badges       = columns.Boolean(default=True)
    show_address      = columns.Boolean(default=True)
    show_links        = columns.Boolean(default=True)
    show_hobbies      = columns.Boolean(default=True)
    show_certificates = columns.Boolean(default=True)
    show_activity     = columns.Boolean(default=False)
    show_contact      = columns.Boolean(default=False)

    # ── Section order (JSON array of section keys) ────────────────────────────
    sections_order  = columns.Text(default='["classrooms","grades","certificates","about"]')

    # ── Privacy ───────────────────────────────────────────────────────────────
    # public | class_only | private
    profile_visibility = columns.Text(default='class_only')

    # ── Flexible metadata (JSON) ──────────────────────────────────────────────
    # Schema:
    # {
    #   "hobbies": ["Lập trình", "Đọc sách"],
    #   "social_links": [{"platform":"github","url":"...","label":"GitHub"}],
    #   "certificates": [{"title":"AWS","issuer":"Amazon","issued_date":"2024-03","url":"..."}],
    #   "custom_fields": [{"key":"Trường học","value":"ĐH Công nghệ"}]
    # }
    metadata = columns.Text(default='{}')

    updated_at = columns.DateTime(default=datetime.utcnow)

    __table_name__ = 'student_profile_settings'

    class Meta:
        get_pk_field = 'consumer_uid'
