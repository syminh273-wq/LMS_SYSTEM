"""Resolve user UID -> email canonical key.

Hệ thống có 2 bảng user: Consumer và Space. Cùng 1 người có thể có 2 UID khác nhau
(1 Consumer + 1 Space) nhưng chung email. Canonical key = email (lowercase, stripped).

Nếu user không có email, fallback về chính UID (giữ behavior cũ).
"""
from __future__ import annotations

import logging
import uuid

logger = logging.getLogger(__name__)


def _email_for_uid(uid) -> str:
    """Tìm email của 1 UID (probe Consumer trước, fallback Space)."""
    try:
        uid_uuid = uuid.UUID(str(uid))
    except Exception:
        return ''
    try:
        from features.account.consumer.models import Consumer
        row = Consumer.objects.filter(uid=uid_uuid, is_deleted=False).first()
        if row and row.email:
            return str(row.email).strip().lower()
    except Exception:
        pass
    try:
        from features.account.space.models import Space
        row = Space.objects.filter(uid=uid_uuid, is_deleted=False).first()
        if row and row.email:
            return str(row.email).strip().lower()
    except Exception:
        pass
    return ''


def pair_key(uid_a, uid_b) -> str:
    """Trả về canonical pair_key = sorted "emailA|emailB" (fallback uid nếu thiếu email)."""
    ea = _email_for_uid(uid_a) or f'uid:{str(uid_a)}'
    eb = _email_for_uid(uid_b) or f'uid:{str(uid_b)}'
    s = sorted([ea, eb])
    return f'{s[0]}|{s[1]}'
