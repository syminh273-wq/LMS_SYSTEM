from datetime import datetime
from uuid import UUID

from core.services.base_service import BaseService
from features.resource.repositories.doc_note_repository import DocNoteRepository
from features.resource.repositories.doc_reading_progress_repository import DocReadingProgressRepository


def _clamp(value, lo, hi):
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


class DocReadingProgressService(BaseService):
    def __init__(self):
        self.repository = DocReadingProgressRepository()
        self.note_repository = DocNoteRepository()

    def get(self, classroom_id, student_id, resource_uid):
        return self.repository.get_for_student_resource(classroom_id, student_id, resource_uid)

    def list_for_student(self, classroom_id, student_id):
        return self.repository.get_for_student(classroom_id, student_id)

    def list_for_resource(self, classroom_id, resource_uid):
        return self.repository.get_for_resource_all_students(classroom_id, resource_uid)

    def compute_progress(self, classroom_id, student_id, resource_uid):
        """Compute progress = max(progress_at of all notes) * 100, capped 99 unless completed.
        is_completed=True → 100."""
        progress = self.get(classroom_id, student_id, resource_uid)
        notes = self.note_repository.get_for_student_resource(resource_uid, student_id)
        max_at = 0.0
        for n in notes:
            try:
                v = float(getattr(n, 'progress_at', 0) or 0)
            except (TypeError, ValueError):
                v = 0
            if v > max_at:
                max_at = v

        derived_pct = int(round(max_at * 100))
        if derived_pct > 99:
            derived_pct = 99
        is_completed = bool(getattr(progress, 'is_completed', False)) if progress else False
        final_pct = 100 if is_completed else derived_pct
        return {
            'read_progress': final_pct,
            'is_completed': is_completed,
            'note_count': len(notes),
        }

    def upsert_progress(self, classroom_id, student_id, resource_uid, data):
        allowed = {}
        if 'read_progress' in data:
            rp = _clamp(data.get('read_progress'), 0, 100)
            if rp is not None:
                allowed['read_progress'] = int(rp)
        if 'is_completed' in data:
            allowed['is_completed'] = bool(data.get('is_completed'))
        allowed['last_opened_at'] = datetime.now()
        return self.repository.upsert(
            classroom_id=classroom_id,
            student_id=student_id,
            resource_uid=resource_uid,
            **allowed,
        )


class DocNoteService(BaseService):
    def __init__(self):
        self.repository = DocNoteRepository()
        self.progress_service = DocReadingProgressService()

    def list_for_resource(self, resource_uid, student_id=None):
        notes = self.repository.get_for_resource(resource_uid)
        if student_id is not None:
            try:
                sid = UUID(str(student_id))
            except (ValueError, TypeError):
                sid = None
            if sid is not None:
                notes = [n for n in notes if getattr(n, 'student_id', None) == sid]
        return notes

    def list_for_student_resource(self, resource_uid, student_id):
        return self.repository.get_for_student_resource(resource_uid, student_id)

    def create(self, classroom_id, student_id, resource_uid, data):
        content = (data.get('content') or '').strip()
        if not content:
            raise ValueError('content is required')

        x_pct = _clamp(data.get('x_pct'), 0, 1)
        y_pct = _clamp(data.get('y_pct'), 0, 1)
        page = data.get('page')
        try:
            page = int(page) if page is not None else None
            if page is not None and page < 1:
                page = 1
        except (TypeError, ValueError):
            page = None

        progress_at = _clamp(data.get('progress_at'), 0, 1) or 0.0
        color = (data.get('color') or 'yellow').strip() or 'yellow'

        try:
            ruid = resource_uid if isinstance(resource_uid, UUID) else UUID(str(resource_uid))
            cid = classroom_id if isinstance(classroom_id, UUID) else UUID(str(classroom_id))
            sid = student_id if isinstance(student_id, UUID) else UUID(str(student_id))
        except (ValueError, TypeError) as exc:
            raise ValueError('Invalid UUID') from exc

        note = self.repository.create(
            resource_uid=ruid,
            classroom_id=cid,
            student_id=sid,
            content=content,
            page=page,
            x_pct=x_pct,
            y_pct=y_pct,
            progress_at=progress_at,
            color=color,
        )

        self._recompute_progress(cid, sid, ruid)
        return note

    def update(self, note, data):
        if 'content' in data:
            new_content = (data.get('content') or '').strip()
            if new_content:
                note.content = new_content
        if 'x_pct' in data:
            v = _clamp(data.get('x_pct'), 0, 1)
            if v is not None:
                note.x_pct = v
        if 'y_pct' in data:
            v = _clamp(data.get('y_pct'), 0, 1)
            if v is not None:
                note.y_pct = v
        if 'page' in data:
            try:
                p = int(data.get('page')) if data.get('page') is not None else None
                if p is not None and p < 1:
                    p = 1
            except (TypeError, ValueError):
                p = None
            note.page = p
        if 'progress_at' in data:
            v = _clamp(data.get('progress_at'), 0, 1)
            if v is not None:
                note.progress_at = v
        if 'color' in data:
            note.color = (data.get('color') or 'yellow').strip() or 'yellow'
        from datetime import datetime as _dt
        note.updated_at = _dt.now()
        note.save()

        self._recompute_progress(note.classroom_id, note.student_id, note.resource_uid)
        return note

    def delete(self, note):
        self.repository.delete(note)
        self._recompute_progress(note.classroom_id, note.student_id, note.resource_uid)

    def _recompute_progress(self, classroom_id, student_id, resource_uid):
        derived = self.progress_service.compute_progress(classroom_id, student_id, resource_uid)
        current = self.progress_service.repository.get_for_student_resource(
            classroom_id, student_id, resource_uid
        )
        if current is None and derived['read_progress'] == 0:
            return
        if current is None:
            self.progress_service.upsert_progress(
                classroom_id=classroom_id,
                student_id=student_id,
                resource_uid=resource_uid,
                data={'read_progress': derived['read_progress']},
            )
        elif int(getattr(current, 'read_progress', 0)) != derived['read_progress']:
            self.progress_service.upsert_progress(
                classroom_id=classroom_id,
                student_id=student_id,
                resource_uid=resource_uid,
                data={'read_progress': derived['read_progress']},
            )

    def find(self, uid):
        return self.repository.find(uid)
