import logging
from datetime import datetime
from features.course.repositories import (
    CourseRepository,
    CourseEnrollmentRepository,
)
from features.course.services.course_service import CourseService

logger = logging.getLogger(__name__)


class CourseEnrollmentService:
    def __init__(self):
        self.course_repo = CourseRepository()
        self.enrollment_repo = CourseEnrollmentRepository()
        self.course_service = CourseService()

    def is_enrolled(self, consumer_id, course_uid) -> bool:
        return self.enrollment_repo.is_enrolled(consumer_id, course_uid)

    def enroll_free(self, consumer, course):
        """Enroll a consumer in a free course. Auto-creates the hidden classroom."""
        from rest_framework.exceptions import ValidationError
        if course.pricing_type != 'free':
            raise ValidationError('Khóa học này là khóa học trả phí, vui lòng thanh toán.')

        classroom = self.course_service.ensure_classroom(course)
        self._ensure_classroom_member(str(consumer.uid), str(classroom.uid), consumer)

        enrollment = self._upsert_enrollment(
            consumer_id=str(consumer.uid),
            course_uid=str(course.uid),
            pricing_type='free',
            amount_vnd=0,
            payment_order_id=None,
        )
        return {
            'enrollment': enrollment,
            'classroom_uid': str(classroom.uid),
            'redirect_to': f'/consumer/classroom/{classroom.uid}',
        }

    def enroll_paid(self, consumer, course, payment_order_id: str):
        """Enroll a consumer in a paid course (called from payment IPN)."""
        classroom = self.course_service.ensure_classroom(course)
        self._ensure_classroom_member(str(consumer.uid), str(classroom.uid), consumer)

        enrollment = self._upsert_enrollment(
            consumer_id=str(consumer.uid),
            course_uid=str(course.uid),
            pricing_type='paid',
            amount_vnd=int(course.price_vnd or 0),
            payment_order_id=payment_order_id,
        )
        return {
            'enrollment': enrollment,
            'classroom_uid': str(classroom.uid),
        }

    def list_for_consumer(self, consumer_id):
        rows = list(self.enrollment_repo.list_for_consumer(consumer_id))
        # Hydrate course
        result = []
        for r in rows:
            try:
                course = self.course_repo.find(r.course_uid)
                result.append({'enrollment': r, 'course': course})
            except Exception:
                continue
        return result

    def list_for_course(self, course_uid):
        rows = list(self.enrollment_repo.list_for_course(course_uid))
        # Hydrate consumer
        from features.account.consumer.repositories import ConsumerRepository
        consumer_repo = ConsumerRepository()
        result = []
        for r in rows:
            try:
                consumer = consumer_repo.find(r.consumer_id)
                result.append({
                    'consumer_id': r.consumer_id,
                    'consumer_name': getattr(consumer, 'full_name', '') or getattr(consumer, 'username', ''),
                    'consumer_avatar': getattr(consumer, 'avatar_url', '') or '',
                    'enrolled_at': r.enrolled_at,
                    'pricing_type': r.pricing_type,
                    'amount_vnd': int(r.amount_vnd or 0),
                    'payment_order_id': r.payment_order_id,
                })
            except Exception:
                continue
        return result

    def get_access(self, consumer_id, course_uid):
        """Returns {enrolled, classroom_uid, redirect_to} for the checkout poller."""
        enrolled = self.is_enrolled(consumer_id, course_uid)
        if not enrolled:
            return {'enrolled': False}
        try:
            course = self.course_repo.find(course_uid)
        except Exception:
            return {'enrolled': False}
        classroom_uid = course.classroom_uid
        return {
            'enrolled': True,
            'classroom_uid': str(classroom_uid) if classroom_uid else None,
            'redirect_to': f'/consumer/classroom/{classroom_uid}' if classroom_uid else None,
        }

    def _ensure_classroom_member(self, consumer_id, classroom_uid, consumer):
        """Insert ClassroomMember with status='approved' (skip pending for course students)."""
        from features.course.classroom.repositories.classroom_member_repository import ClassroomMemberRepository
        member_repo = ClassroomMemberRepository()
        existing = member_repo.get_member(classroom_uid, consumer_id)
        if existing and not existing.is_deleted and existing.status == 'approved':
            return existing

        name = getattr(consumer, 'full_name', '') or getattr(consumer, 'username', '') or ''
        avatar = getattr(consumer, 'avatar_url', '') or ''

        if existing:
            member_repo.update(existing, is_deleted=False, status='approved')
            return existing

        return member_repo.create(
            member_id=consumer_id,
            classroom_uid=classroom_uid,
            member_type='consumer',
            member_name=name,
            member_avatar=avatar,
            role='student',
            status='approved',
        )

    def _upsert_enrollment(self, consumer_id, course_uid, pricing_type, amount_vnd, payment_order_id):
        existing = self.enrollment_repo.get_for_consumer(consumer_id, course_uid)
        if existing:
            return self.enrollment_repo.update(
                existing,
                is_deleted=False,
                status='enrolled',
                enrolled_at=datetime.utcnow(),
                pricing_type=pricing_type,
                amount_vnd=amount_vnd,
                payment_order_id=payment_order_id,
            )
        return self.enrollment_repo.create(
            consumer_id=consumer_id,
            course_uid=course_uid,
            status='enrolled',
            enrolled_at=datetime.utcnow(),
            pricing_type=pricing_type,
            amount_vnd=amount_vnd,
            payment_order_id=payment_order_id,
        )
