"""
LMSIndexer — called directly from services after create/update/delete.

Cassandra models do not reliably fire Django post_save/post_delete signals,
so we hook at the service layer instead of using signal handlers.

Usage:
    from core.search_engine.typesense.indexer import LMSIndexer

    # After create/update:
    LMSIndexer.index(classroom_instance)

    # After soft-delete or hard delete:
    LMSIndexer.remove_classroom(uid)
"""

from __future__ import annotations

from typing import Any

from core.search_engine.typesense.service import TypesenseService


def _ts(dt) -> int:
    """DateTime → unix timestamp int."""
    if dt is None:
        return 0
    try:
        return int(dt.timestamp())
    except Exception:
        return 0


# ── Transformers ──────────────────────────────────────────────────────────────

def _classroom_doc(c) -> dict:
    return {
        'id':           str(c.uid),
        'uid':          str(c.uid),
        'pid':          c.pid or '',
        'name':         c.name or '',
        'description':  c.description or '',
        'teacher_id':   str(c.teacher_id),
        'max_students': int(c.max_students or 0),
        'status':       c.status or 'active',
        'is_deleted':   bool(getattr(c, 'is_deleted', False)),
        'created_at':   _ts(getattr(c, 'created_at', None)),
        'updated_at':   _ts(getattr(c, 'updated_at', None)),
    }


def _exam_doc(e) -> dict:
    return {
        'id':           str(e.uid),
        'uid':          str(e.uid),
        'classroom_id': str(e.classroom_id),
        'teacher_id':   str(e.teacher_id),
        'title':        e.title or '',
        'description':  e.description or '',
        'body':         (e.body or '')[:500],  # cap body for index size
        'status':       e.status or 'draft',
        'exam_type':    getattr(e, 'exam_type', 'assignment') or 'assignment',
        'content_type': e.content_type or '',
        'exam_mode':    getattr(e, 'exam_mode', 'offline') or 'offline',
        'is_deleted':   bool(getattr(e, 'is_deleted', False)),
        'created_at':   _ts(getattr(e, 'created_at', None)),
        'updated_at':   _ts(getattr(e, 'updated_at', None)),
    }


def _consumer_doc(c) -> dict:
    return {
        'id':         str(c.uid),
        'uid':        str(c.uid),
        'pid':        getattr(c, 'pid', '') or '',
        'username':   c.username or '',
        'email':      c.email or '',
        'first_name': getattr(c, 'first_name', '') or '',
        'last_name':  getattr(c, 'last_name', '') or '',
        'full_name':  c.full_name or '',
        'phone':      c.phone or '',
        'role':       getattr(c, 'role', 'student') or 'student',
        'is_active':  bool(getattr(c, 'is_active', True)),
        'is_deleted': bool(getattr(c, 'is_deleted', False)),
        'created_at': _ts(getattr(c, 'created_at', None)),
    }


def _teacher_contact_doc(tc) -> dict:
    return {
        'id':             f"{tc.teacher_id}_{tc.consumer_uid}",
        'teacher_id':     str(tc.teacher_id),
        'consumer_uid':   str(tc.consumer_uid),
        'consumer_name':  tc.consumer_name or '',
        'first_name':     getattr(tc, 'first_name', '') or '',
        'last_name':      getattr(tc, 'last_name', '') or '',
        'consumer_email': tc.consumer_email or '',
        'consumer_avatar': tc.consumer_avatar or '',
        'first_joined_at': _ts(getattr(tc, 'first_joined_at', None)),
    }


def _space_doc(s) -> dict:
    return {
        'id':          str(s.uid),
        'uid':         str(s.uid),
        'email':       s.email or '',
        'full_name':   s.full_name or '',
        'name':        s.name or '',
        'slug':        s.slug or '',
        'description': s.description or '',
        'is_active':   bool(getattr(s, 'is_active', True)),
        'is_deleted':  bool(getattr(s, 'is_deleted', False)),
        'created_at':  _ts(getattr(s, 'created_at', None)),
    }


def _quiz_doc(q) -> dict:
    return {
        'id':               str(q.uid),
        'uid':              str(q.uid),
        'created_by':       str(q.created_by),
        'title':            q.title or '',
        'description':      q.description or '',
        'questions_count':  int(q.questions_count or 0),
        'status':           q.status or 'draft',
        'is_deleted':       bool(getattr(q, 'is_deleted', False)),
        'created_at':       _ts(getattr(q, 'created_at', None)),
        'updated_at':       _ts(getattr(q, 'updated_at', None)),
    }


def _resource_doc(r) -> dict:
    return {
        'id':         str(r.uid),
        'uid':        str(r.uid),
        'name':       r.name or '',
        'file_type':  r.file_type or 'unknown',
        'url':        r.url or '',
        'size':       int(r.size or 0),
        'owner_id':   str(r.owner_id) if r.owner_id else '',
        'owner_type': r.owner_type or '',
        'is_deleted': bool(getattr(r, 'is_deleted', False)),
        'created_at': _ts(getattr(r, 'created_at', None)),
    }


def _course_doc(c) -> dict:
    return {
        'id':           str(c.uid),
        'uid':          str(c.uid),
        'pid':          c.pid or '',
        'name':         c.name or '',
        'description':  c.description or '',
        'teacher_id':   str(c.teacher_id),
        'pricing_type': c.pricing_type or 'free',
        'price_vnd':    int(c.price_vnd or 0),
        'status':       c.status or 'draft',
        'is_deleted':   bool(getattr(c, 'is_deleted', False)),
        'created_at':   _ts(getattr(c, 'created_at', None)),
        'updated_at':   _ts(getattr(c, 'updated_at', None)),
    }


# ── Model → (collection, transformer) map ────────────────────────────────────

_COLLECTION_MAP: dict[str, tuple[str, Any]] = {
    'Classroom':      ('lms_classroom',       _classroom_doc),
    'Exam':           ('lms_exam',            _exam_doc),
    'Consumer':       ('lms_consumer',        _consumer_doc),
    'Space':          ('lms_space',           _space_doc),
    'Quiz':           ('lms_quiz',            _quiz_doc),
    'Resource':       ('lms_resource',        _resource_doc),
    'TeacherContact': ('lms_teacher_contact', _teacher_contact_doc),
    'Course':         ('lms_course',          _course_doc),
}


class LMSIndexer:
    """
    Called directly from service layer to keep Typesense in sync.
    All methods are safe to call — they never raise exceptions.
    """

    _svc: TypesenseService | None = None

    @classmethod
    def _service(cls) -> TypesenseService:
        if cls._svc is None:
            cls._svc = TypesenseService()
        return cls._svc

    # ── Generic ───────────────────────────────────────────────────────────────

    @classmethod
    def index(cls, instance) -> None:
        model_name = type(instance).__name__
        if model_name not in _COLLECTION_MAP:
            return
        collection, transformer = _COLLECTION_MAP[model_name]
        try:
            doc = transformer(instance)
            cls._service().upsert(collection, doc)
        except Exception:
            pass

    @classmethod
    def remove(cls, model_name: str, uid: str) -> None:
        if model_name not in _COLLECTION_MAP:
            return
        collection, _ = _COLLECTION_MAP[model_name]
        cls._service().remove(collection, uid)

    # ── Convenience shortcuts ─────────────────────────────────────────────────

    @classmethod
    def index_classroom(cls, c) -> None:
        cls._service().upsert('lms_classroom', _classroom_doc(c))

    @classmethod
    def remove_classroom(cls, uid: str) -> None:
        cls._service().remove('lms_classroom', str(uid))

    @classmethod
    def index_exam(cls, e) -> None:
        cls._service().upsert('lms_exam', _exam_doc(e))

    @classmethod
    def remove_exam(cls, uid: str) -> None:
        cls._service().remove('lms_exam', str(uid))

    @classmethod
    def index_consumer(cls, c) -> None:
        cls._service().upsert('lms_consumer', _consumer_doc(c))

    @classmethod
    def remove_consumer(cls, uid: str) -> None:
        cls._service().remove('lms_consumer', str(uid))

    @classmethod
    def index_space(cls, s) -> None:
        cls._service().upsert('lms_space', _space_doc(s))

    @classmethod
    def remove_space(cls, uid: str) -> None:
        cls._service().remove('lms_space', str(uid))

    @classmethod
    def index_quiz(cls, q) -> None:
        cls._service().upsert('lms_quiz', _quiz_doc(q))

    @classmethod
    def remove_quiz(cls, uid: str) -> None:
        cls._service().remove('lms_quiz', str(uid))

    @classmethod
    def index_resource(cls, r) -> None:
        cls._service().upsert('lms_resource', _resource_doc(r))

    @classmethod
    def remove_resource(cls, uid: str) -> None:
        cls._service().remove('lms_resource', str(uid))

    @classmethod
    def index_teacher_contact(cls, tc) -> None:
        cls._service().upsert('lms_teacher_contact', _teacher_contact_doc(tc))

    @classmethod
    def remove_teacher_contact(cls, teacher_id: str, consumer_uid: str) -> None:
        cls._service().remove('lms_teacher_contact', f"{teacher_id}_{consumer_uid}")

    @classmethod
    def index_course(cls, c) -> None:
        cls._service().upsert('lms_course', _course_doc(c))

    @classmethod
    def remove_course(cls, uid: str) -> None:
        cls._service().remove('lms_course', str(uid))

    # ── Backfill helpers ─────────────────────────────────────────────────────

    BACKFILL_MAP = {
        'lms_classroom':       ('features.course.classroom.models',         'Classroom',     _classroom_doc),
        'lms_exam':            ('features.course.exam.models',              'Exam',          _exam_doc),
        'lms_consumer':        ('features.account.consumer.models',         'Consumer',      _consumer_doc),
        'lms_space':           ('features.account.space.models',            'Space',         _space_doc),
        'lms_quiz':            ('features.quiz.models',                     'Quiz',          _quiz_doc),
        'lms_resource':        ('features.resource.models',                 'Resource',      _resource_doc),
        'lms_teacher_contact': ('features.course.classroom.models.teacher_contact', 'TeacherContact', _teacher_contact_doc),
    }
