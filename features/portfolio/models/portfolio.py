from cassandra.cqlengine import columns
from core.models.cassandra import BaseTimeStampModel
from core.utils.uuid import uuid7


class Portfolio(BaseTimeStampModel):
    """
    Polymorphic key-value profile table — dùng chung cho Consumer và Space.

    Mỗi (owner_id, owner_type, key) là 1 row. Query "lấy tất cả profile của user X"
    = 1 partition scan trên (owner_id, owner_type).

    Keys hợp lệ (Portfolio.VALID_KEYS):
        - Profile:       bio, city, country, major, department
        - Social links:  github, linkedin, website, skills
        - Appearance:    theme_color, cover_style, cover_value
        - Privacy:       profile_visibility, show_stats, show_classrooms, show_grades,
                         show_badges, show_address, show_links, show_hobbies,
                         show_certificates, show_activity, show_contact
        - Layout:        sections_order
        - Flexible:      metadata
        - Rich entries:  intro, certificate, experience, achievement, course, education
    """

    __table_name__ = 'portfolios'

    uid        = columns.UUID(primary_key=True, default=uuid7)
    owner_id   = columns.UUID(partition_key=True, required=True)
    owner_type = columns.Text(partition_key=True, required=True)
    key        = columns.Text(primary_key=True, required=True)

    value         = columns.Text(default='{}')
    is_public     = columns.Boolean(default=True)
    display_order = columns.Integer(default=0)
    metadata      = columns.Map(columns.Text, columns.Text, default=dict)

    class Meta:
        get_pk_field = 'uid'

    VALID_KEYS = (
        'bio', 'city', 'country', 'major', 'department',
        'github', 'linkedin', 'website', 'skills',
        'theme_color', 'cover_style', 'cover_value',
        'profile_visibility',
        'show_stats', 'show_classrooms', 'show_grades', 'show_badges',
        'show_address', 'show_links', 'show_hobbies', 'show_certificates',
        'show_activity', 'show_contact',
        'sections_order',
        'intro', 'certificate', 'experience', 'achievement', 'course', 'education',
    )

    OWNER_TYPES = ('space', 'consumer')

    SINGLE_KEYS = frozenset({
        'bio', 'city', 'country', 'major', 'department',
        'github', 'linkedin', 'website', 'skills',
        'theme_color', 'cover_style', 'cover_value',
        'profile_visibility', 'sections_order',
    })

    PRIVACY_KEYS = frozenset({
        'profile_visibility',
        'show_stats', 'show_classrooms', 'show_grades', 'show_badges',
        'show_address', 'show_links', 'show_hobbies', 'show_certificates',
        'show_activity', 'show_contact',
    })

    APPEARANCE_KEYS = frozenset({
        'theme_color', 'cover_style', 'cover_value',
    })

    PROFILE_KEYS = frozenset({
        'bio', 'city', 'country', 'major', 'department',
        'github', 'linkedin', 'website', 'skills',
        'sections_order',
    })

    RICH_KEYS = frozenset({
        'intro', 'certificate', 'experience', 'achievement', 'course', 'education',
    })
