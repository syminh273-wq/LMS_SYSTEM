from typing import Any, Dict, List, Optional


class TypesenseSchema:
    """Registry for Typesense collection schemas."""

    _registry: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register(cls, name: str, schema: Dict[str, Any]) -> None:
        cls._registry[name] = schema

    @classmethod
    def get(cls, name: str) -> Optional[Dict[str, Any]]:
        return cls._registry.get(name)

    @classmethod
    def all(cls) -> Dict[str, Dict[str, Any]]:
        return dict(cls._registry)

    @classmethod
    def names(cls) -> List[str]:
        return list(cls._registry.keys())


# ── LMS Collection Schemas ────────────────────────────────────────────────────

TypesenseSchema.register('lms_classroom', {
    'name': 'lms_classroom',
    'fields': [
        {'name': 'id',          'type': 'string'},
        {'name': 'uid',         'type': 'string'},
        {'name': 'pid',         'type': 'string', 'infix': True},
        {'name': 'name',        'type': 'string', 'locale': 'vi', 'infix': True},
        {'name': 'description', 'type': 'string', 'locale': 'vi', 'optional': True},
        {'name': 'teacher_id',  'type': 'string'},
        {'name': 'max_students','type': 'int32'},
        {'name': 'status',      'type': 'string', 'facet': True},
        {'name': 'is_deleted',  'type': 'bool'},
        {'name': 'created_at',  'type': 'int64'},
        {'name': 'updated_at',  'type': 'int64', 'optional': True},
    ],
    'default_sorting_field': 'created_at',
})

TypesenseSchema.register('lms_exam', {
    'name': 'lms_exam',
    'fields': [
        {'name': 'id',           'type': 'string'},
        {'name': 'uid',          'type': 'string'},
        {'name': 'classroom_id', 'type': 'string'},
        {'name': 'teacher_id',   'type': 'string'},
        {'name': 'title',        'type': 'string', 'locale': 'vi', 'infix': True},
        {'name': 'description',  'type': 'string', 'locale': 'vi', 'optional': True},
        {'name': 'body',         'type': 'string', 'optional': True},
        {'name': 'status',       'type': 'string', 'facet': True},
        {'name': 'exam_type',    'type': 'string', 'facet': True},
        {'name': 'content_type', 'type': 'string', 'facet': True},
        {'name': 'exam_mode',    'type': 'string', 'facet': True},
        {'name': 'is_deleted',   'type': 'bool'},
        {'name': 'created_at',   'type': 'int64'},
        {'name': 'updated_at',   'type': 'int64', 'optional': True},
    ],
    'default_sorting_field': 'created_at',
})

TypesenseSchema.register('lms_consumer', {
    'name': 'lms_consumer',
    'fields': [
        {'name': 'id',         'type': 'string'},
        {'name': 'uid',        'type': 'string'},
        {'name': 'username',   'type': 'string', 'infix': True},
        {'name': 'email',      'type': 'string', 'infix': True},
        {'name': 'full_name',  'type': 'string', 'locale': 'vi', 'infix': True},
        {'name': 'phone',      'type': 'string', 'optional': True, 'infix': True},
        {'name': 'role',       'type': 'string', 'facet': True},
        {'name': 'is_active',  'type': 'bool'},
        {'name': 'is_deleted', 'type': 'bool'},
        {'name': 'created_at', 'type': 'int64'},
    ],
    'default_sorting_field': 'created_at',
})

TypesenseSchema.register('lms_space', {
    'name': 'lms_space',
    'fields': [
        {'name': 'id',          'type': 'string'},
        {'name': 'uid',         'type': 'string'},
        {'name': 'email',       'type': 'string', 'infix': True},
        {'name': 'full_name',   'type': 'string', 'locale': 'vi', 'infix': True},
        {'name': 'name',        'type': 'string', 'locale': 'vi', 'infix': True},
        {'name': 'slug',        'type': 'string', 'infix': True},
        {'name': 'description', 'type': 'string', 'locale': 'vi', 'optional': True},
        {'name': 'is_active',   'type': 'bool'},
        {'name': 'is_deleted',  'type': 'bool'},
        {'name': 'created_at',  'type': 'int64'},
    ],
    'default_sorting_field': 'created_at',
})

TypesenseSchema.register('lms_quiz', {
    'name': 'lms_quiz',
    'fields': [
        {'name': 'id',              'type': 'string'},
        {'name': 'uid',             'type': 'string'},
        {'name': 'created_by',      'type': 'string'},
        {'name': 'title',           'type': 'string', 'locale': 'vi', 'infix': True},
        {'name': 'description',     'type': 'string', 'locale': 'vi', 'optional': True},
        {'name': 'questions_count', 'type': 'int32'},
        {'name': 'status',          'type': 'string', 'facet': True},
        {'name': 'is_deleted',      'type': 'bool'},
        {'name': 'created_at',      'type': 'int64'},
        {'name': 'updated_at',      'type': 'int64', 'optional': True},
    ],
    'default_sorting_field': 'created_at',
})
