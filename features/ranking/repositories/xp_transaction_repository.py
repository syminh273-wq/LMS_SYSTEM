import json
from uuid import UUID
from datetime import datetime

from core.repositories.base_repository import BaseRepository
from features.ranking.models.xp_transaction import XPTransaction


class XPTransactionRepository(BaseRepository):
    model = XPTransaction

    def create(self, **kwargs):
        metadata = kwargs.pop('metadata', None)
        if metadata is not None and not isinstance(metadata, str):
            metadata = json.dumps(metadata, ensure_ascii=False, default=str)
        if metadata is not None:
            kwargs['metadata'] = metadata
        return super().create(**kwargs)

    def list_by_student(self, student_id, limit=20, event_type=None, classroom_id=None):
        """Return all matching transactions for a student (newest first).

        Partition is `student_id`, so fetching the full partition is cheap
        (one student rarely has more than a few hundred events). Filtering
        by `event_type` / `classroom_id` is done in Python after the
        partition read, so `limit` only applies to the *filtered* result.
        """
        try:
            sid = student_id if isinstance(student_id, UUID) else UUID(str(student_id))
        except (ValueError, TypeError):
            return []

        rows = list(self.model.objects(student_id=sid))
        if event_type:
            rows = [r for r in rows if r.event_type == event_type]
        if classroom_id:
            try:
                cid = UUID(str(classroom_id))
            except (ValueError, TypeError):
                cid = None
            if cid is not None:
                rows = [r for r in rows if r.classroom_id == cid]

        if limit is not None and limit > 0:
            rows = rows[: int(limit)]
        return rows

    def sum_xp_in_classroom(self, student_id, classroom_id) -> int:
        try:
            sid = student_id if isinstance(student_id, UUID) else UUID(str(student_id))
            cid = classroom_id if isinstance(classroom_id, UUID) else UUID(str(classroom_id))
        except (ValueError, TypeError):
            return 0
        try:
            qs = self.model.objects(student_id=sid, classroom_id=cid).allow_filtering()
        except Exception:
            return 0
        return sum(int(getattr(t, 'delta_xp', 0) or 0) for t in qs)

    def exists_for_ref(self, student_id, event_type, ref_type, ref_id):
        """Idempotency: has this exact event already been recorded for the student?"""
        try:
            sid = student_id if isinstance(student_id, UUID) else UUID(str(student_id))
            rid = ref_id if isinstance(ref_id, UUID) else UUID(str(ref_id))
        except (ValueError, TypeError):
            return False
        qs = self.model.objects(student_id=sid, event_type=event_type).allow_filtering()
        for row in qs:
            if row.ref_type == ref_type and row.ref_id == rid:
                return True
        return False
