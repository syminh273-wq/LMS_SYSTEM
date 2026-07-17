import uuid as _uuid
from datetime import datetime

from features.resource.services import DocNoteService, DocReadingProgressService
from features.resource.serializers.doc_progress_note_serializer import (
    DocReadingProgressResponseSerializer,
    DocNoteResponseSerializer,
)


def _serialize_progress(classroom_id, student_id, resource_uid, computed):
    return {
        'classroom_id': str(classroom_id),
        'student_id': str(student_id),
        'resource_uid': str(resource_uid),
        'read_progress': computed['read_progress'],
        'is_completed': computed['is_completed'],
        'note_count': computed['note_count'],
        'completed_at': None,
        'last_opened_at': datetime.now().isoformat(),
    }


def _serialize_note(note):
    return {
        'uid': str(note.uid),
        'resource_uid': str(note.resource_uid),
        'classroom_id': str(note.classroom_id),
        'student_id': str(note.student_id),
        'content': note.content,
        'page': getattr(note, 'page', None),
        'x_pct': getattr(note, 'x_pct', None),
        'y_pct': getattr(note, 'y_pct', None),
        'progress_at': float(getattr(note, 'progress_at', 0) or 0),
        'color': getattr(note, 'color', 'yellow'),
        'created_at': note.created_at.isoformat() if getattr(note, 'created_at', None) else None,
        'updated_at': note.updated_at.isoformat() if getattr(note, 'updated_at', None) else None,
    }


def get_student_progress(classroom_uid, student_id, resource_uid):
    progress_service = DocReadingProgressService()
    computed = progress_service.compute_progress(classroom_id=classroom_uid, student_id=student_id, resource_uid=resource_uid)
    return _serialize_progress(classroom_uid, student_id, resource_uid, computed)


def mark_progress(classroom_uid, student_id, resource_uid, data):
    progress_service = DocReadingProgressService()
    progress_service.upsert_progress(
        classroom_id=classroom_uid,
        student_id=student_id,
        resource_uid=resource_uid,
        data=data or {},
    )
    return get_student_progress(classroom_uid, student_id, resource_uid)


def mark_completed(classroom_uid, student_id, resource_uid, is_completed=True):
    progress_service = DocReadingProgressService()
    if is_completed:
        progress_service.upsert_progress(
            classroom_id=classroom_uid,
            student_id=student_id,
            resource_uid=resource_uid,
            data={'is_completed': True, 'read_progress': 100},
        )
    else:
        progress_service.upsert_progress(
            classroom_id=classroom_uid,
            student_id=student_id,
            resource_uid=resource_uid,
            data={'is_completed': False},
        )
    return get_student_progress(classroom_uid, student_id, resource_uid)


def list_notes_for_resource(resource_uid, student_id=None):
    note_service = DocNoteService()
    notes = note_service.list_for_resource(resource_uid, student_id=student_id)
    return [_serialize_note(n) for n in notes]


def create_note(classroom_uid, student_id, resource_uid, data):
    note_service = DocNoteService()
    note = note_service.create(
        classroom_id=classroom_uid,
        student_id=student_id,
        resource_uid=resource_uid,
        data=data or {},
    )
    return _serialize_note(note)


def update_note(note, data):
    note_service = DocNoteService()
    updated = note_service.update(note, data or {})
    return _serialize_note(updated)


def delete_note(note):
    note_service = DocNoteService()
    note_service.delete(note)
    return True


def list_progress_for_resource_all_students(classroom_uid, resource_uid):
    progress_service = DocReadingProgressService()
    out = []
    for p in progress_service.list_for_resource(classroom_uid, resource_uid):
        computed = progress_service.compute_progress(classroom_uid, p.student_id, resource_uid)
        out.append({
            **_serialize_progress(classroom_uid, p.student_id, resource_uid, computed),
            'completed_at': p.completed_at.isoformat() if getattr(p, 'completed_at', None) else None,
            'last_opened_at': p.last_opened_at.isoformat() if getattr(p, 'last_opened_at', None) else None,
        })
    return out
