import base64
import json
import logging
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from core.services.base_service import BaseService

logger = logging.getLogger(__name__)

MAX_PAYMENTS_PER_QUERY = 2000

STATUS_KEYS = ('pending', 'completed', 'failed', 'cancelled')
STATUS_LABEL = {
    'pending': 'Đang chờ',
    'completed': 'Thành công',
    'failed': 'Thất bại',
    'cancelled': 'Đã hoàn tiền',
}


def _decode_meta(extra_data: str | None) -> dict:
    if not extra_data:
        return {}
    try:
        return json.loads(base64.b64decode(extra_data).decode())
    except Exception:
        return {}


def _bucket_key(dt: datetime, granularity: str) -> str:
    if granularity == 'day':
        return dt.strftime('%Y-%m-%d')
    if granularity == 'week':
        iso = dt.isocalendar()
        return f'{iso.year}-W{iso.week:02d}'
    return dt.strftime('%Y-%m')


def _infer_granularity(from_dt: datetime | None, to_dt: datetime | None) -> str:
    if not from_dt or not to_dt:
        return 'day'
    span_days = (to_dt - from_dt).days
    if span_days <= 31:
        return 'day'
    if span_days <= 84:
        return 'week'
    return 'month'


class PaymentAnalyticsService(BaseService):
    """Aggregate payment data for the space (teacher) dashboard.

    Cassandra caveat: the `Payment` model only has indexed columns
    `teacher_id` and `status`, so we fetch by `teacher_id` (with
    `is_deleted=False`) and filter the rest in Python. We cap the
    query at ``MAX_PAYMENTS_PER_QUERY`` rows and surface an
    ``approximated`` flag when the cap is hit.
    """

    def __init__(self) -> None:
        from features.payment.repositories import PaymentRepository

        self.repo = PaymentRepository()

    def get_summary(
        self,
        teacher_id: str,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        status: str | None = None,
        resource_id: str | None = None,
        bucket: str | None = None,
    ) -> dict:
        payments = self._fetch_payments(teacher_id=teacher_id, status=status)

        truncated = False
        if len(payments) >= MAX_PAYMENTS_PER_QUERY:
            truncated = True
            payments = payments[:MAX_PAYMENTS_PER_QUERY]

        if from_dt or to_dt:
            payments = self._filter_by_date(payments, from_dt, to_dt)

        if resource_id:
            payments = self._filter_by_resource(payments, resource_id)

        granularity = bucket or _infer_granularity(from_dt, to_dt)

        kpis = self._aggregate_kpis(payments)
        status_distribution = self._aggregate_status(payments)
        revenue_trend = self._aggregate_trend(payments, granularity)
        by_classroom = self._aggregate_by_classroom(payments)

        return {
            'kpis': kpis,
            'status_distribution': status_distribution,
            'revenue_trend': revenue_trend,
            'by_classroom': by_classroom,
            'filters': {
                'from': from_dt.isoformat() if from_dt else None,
                'to': to_dt.isoformat() if to_dt else None,
                'status': status,
                'resource_id': resource_id,
                'bucket': granularity,
            },
            'approximated': truncated,
        }

    # ── data fetching ────────────────────────────────────────────────────
    def _fetch_payments(self, teacher_id: str, status: str | None) -> list:
        try:
            qs = self.repo.get_by_teacher(teacher_id, status=status, limit=MAX_PAYMENTS_PER_QUERY)
            return list(qs)
        except Exception as exc:
            logger.exception('[PaymentAnalytics] fetch failed: %s', exc)
            return []

    @staticmethod
    def _filter_by_date(payments: Iterable, from_dt: datetime | None, to_dt: datetime | None) -> list:
        out = []
        for p in payments:
            created = getattr(p, 'created_at', None)
            if not created:
                continue
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if from_dt and created < from_dt:
                continue
            if to_dt and created > to_dt:
                continue
            out.append(p)
        return out

    @staticmethod
    def _filter_by_resource(payments: Iterable, resource_id: str) -> list:
        target = str(resource_id)
        return [
            p for p in payments
            if str(_decode_meta(getattr(p, 'extra_data', '')).get('resource_id') or '') == target
        ]

    # ── aggregations ────────────────────────────────────────────────────
    @staticmethod
    def _aggregate_kpis(payments: list) -> dict:
        total_revenue = 0
        total_paid = 0
        total_pending = 0
        refunded = 0
        failed = 0
        for p in payments:
            amount = int(getattr(p, 'amount', 0) or 0)
            status = (getattr(p, 'status', '') or '').lower()
            if status == 'completed':
                total_revenue += amount
                total_paid += amount
            elif status == 'pending':
                total_pending += amount
            elif status == 'cancelled':
                refunded += amount
            elif status == 'failed':
                failed += 1
        return {
            'total_revenue': total_revenue,
            'total_transactions': len(payments),
            'total_paid_amount': total_paid,
            'total_pending_amount': total_pending,
            'refunded_amount': refunded,
            'failed_count': failed,
        }

    @staticmethod
    def _aggregate_status(payments: list) -> list:
        counts: dict[str, int] = {k: 0 for k in STATUS_KEYS}
        amounts: dict[str, int] = {k: 0 for k in STATUS_KEYS}
        for p in payments:
            s = (getattr(p, 'status', '') or '').lower()
            if s not in counts:
                continue
            counts[s] += 1
            amounts[s] += int(getattr(p, 'amount', 0) or 0)
        total = sum(counts.values()) or 1
        out = []
        for key in STATUS_KEYS:
            pct = round((counts[key] / total) * 100, 1) if total else 0.0
            out.append({
                'status': key,
                'label': STATUS_LABEL[key],
                'count': counts[key],
                'amount': amounts[key],
                'percentage': pct,
            })
        return out

    @staticmethod
    def _aggregate_trend(payments: list, granularity: str) -> list:
        buckets: 'OrderedDict[str, dict]' = OrderedDict()
        for p in payments:
            created = getattr(p, 'created_at', None)
            if not created:
                continue
            status = (getattr(p, 'status', '') or '').lower()
            amount = int(getattr(p, 'amount', 0) or 0)
            key = _bucket_key(created, granularity)
            entry = buckets.setdefault(key, {'date': key, 'revenue': 0, 'transaction_count': 0})
            if status == 'completed':
                entry['revenue'] += amount
            entry['transaction_count'] += 1
        return list(buckets.values())

    def _aggregate_by_classroom(self, payments: list) -> list:
        groups: dict[str, dict] = {}
        for p in payments:
            meta = _decode_meta(getattr(p, 'extra_data', ''))
            if meta.get('resource_type') != 'classroom':
                continue
            rid = str(meta.get('resource_id') or '')
            if not rid:
                continue
            entry = groups.setdefault(rid, {
                'classroom_uid': rid,
                'classroom_name': rid,
                'total_count': 0,
                'completed_count': 0,
                'pending_count': 0,
                'total_revenue': 0,
            })
            status = (getattr(p, 'status', '') or '').lower()
            amount = int(getattr(p, 'amount', 0) or 0)
            entry['total_count'] += 1
            if status == 'completed':
                entry['completed_count'] += 1
                entry['total_revenue'] += amount
            elif status == 'pending':
                entry['pending_count'] += 1

        if not groups:
            return []

        names = self._lookup_classroom_names(list(groups.keys()))
        for uid, entry in groups.items():
            if uid in names:
                entry['classroom_name'] = names[uid]

        return sorted(groups.values(), key=lambda x: x['total_revenue'], reverse=True)

    @staticmethod
    def _lookup_classroom_names(uids: list[str]) -> dict[str, str]:
        if not uids:
            return {}
        try:
            from features.course.classroom.repositories import Repository
            repo = Repository()
            names: dict[str, str] = {}
            for uid in uids:
                try:
                    classroom = repo.find(uid)
                    names[uid] = getattr(classroom, 'name', uid) or uid
                except Exception:
                    continue
            return names
        except Exception as exc:
            logger.warning('[PaymentAnalytics] classroom lookup failed: %s', exc)
            return {}


def parse_date_param(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        cleaned = raw.replace('Z', '+00:00')
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def default_window(days: int = 30) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    return now - timedelta(days=days), now
