import json
import secrets
from datetime import date, datetime, timedelta

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand

from core.utils.pid import generate_pid
from core.utils.uuid import uuid7

from features.account.consumer.enums import ConsumerRole
from features.account.consumer.models.address import Address
from features.account.consumer.models.consumer import Consumer
from features.account.otp.models.otp_record import OTPRecord
from features.account.space.models.space import Space
from features.account.user_setting.enums import UserTypes
from features.account.user_setting.models.user_setting import UserSetting

from features.course.classroom.models.classroom import Classroom
from features.course.classroom.models.classroom_activity_log import ClassroomActivityLog
from features.course.classroom.models.classroom_member import ClassroomMember
from features.course.classroom.models.teacher_blacklist import GLOBAL_SENTINEL, TeacherBlacklist
from features.course.classroom.models.teacher_contact import TeacherContact

from features.course.exam.models.exam import Exam
from features.course.exam.models.exam_event_log import ExamEventLog
from features.course.exam.models.exam_session import ExamSession
from features.course.exam.models.exam_submission import ExamSubmission

from features.course.meeting_room.models.meeting_room import MeetingRoom
from features.course.meeting_room.models.meeting_room_participant import MeetingRoomParticipant

from features.quiz.models.quiz import Quiz
from features.quiz.models.quiz_assignment import QuizAssignment
from features.quiz.models.quiz_log import QuizLog
from features.quiz.models.quiz_question import QuizQuestion

from features.quiz_collection.models.certificate import Certificate
from features.quiz_collection.models.issued_certificate import IssuedCertificate
from features.quiz_collection.models.quiz_collection import QuizCollection
from features.quiz_collection.models.quiz_collection_assignment import QuizCollectionAssignment

from features.resource.models.resource import Resource
from features.resource.services.resource_folder_seed_service import ResourceFolderSeedService

from features.chat.models.conversation import Conversation
from features.chat.models.conversation_member import ConversationMember
from features.chat.models.message import Message

from features.calendar.models.attendance import Attendance
from features.calendar.models.calendar_event import CalendarEvent
from features.calendar.models.leave_request import LeaveRequest

from features.notification.models.notification_log import NotificationLog

from features.payment.enums import PaymentStatus
from features.payment.models.payment import Payment

from features.portfolio.models.portfolio import Portfolio

from features.ranking.enums import XpEvent, XP_AMOUNTS, XP_DESCRIPTIONS
from features.ranking.models.achievement import StudentAchievement
from features.ranking.models.student_xp import StudentXP
from features.ranking.models.xp_transaction import XPTransaction

from features.social.models.classroom_favorite import ClassroomFavorite
from features.social.models.post import SocialPost
from features.social.models.post_comment import SocialPostComment
from features.social.models.post_like import SocialPostLike
from features.social.models.social_follow import SocialFollow
from features.social.models.social_profile import SocialProfile

from features.face.models.face_embedding import FaceEmbedding

from features.ai.models.ai_conversation_session import AIConversationSession
from features.ai.repositories.ai_message_repository import AIMessageRepository

SPACE_EMAIL = 'testspace@gmail.com'
CONSUMER_EMAIL = 'testconsumer@gmail.com'
DEMO_PASSWORD = '123456'
DEMO_CLASSROOM_NAME = 'Lập trình Web Full-stack'

CLASSMATES = [
    {'email': 'lethiminhanh.demo@lms-demo.test', 'first_name': 'Lê', 'last_name': 'Thị Minh Anh', 'phone': '0911111111'},
    {'email': 'phamquocbao.demo@lms-demo.test', 'first_name': 'Phạm', 'last_name': 'Quốc Bảo', 'phone': '0922222222'},
    {'email': 'dothithuha.demo@lms-demo.test', 'first_name': 'Đỗ', 'last_name': 'Thị Thu Hà', 'phone': '0933333333'},
]
PENDING_STUDENT = {'email': 'hoangvancho.demo@lms-demo.test', 'first_name': 'Hoàng', 'last_name': 'Văn Chờ', 'phone': '0944444444'}
BANNED_STUDENT = {'email': 'vubican.demo@lms-demo.test', 'first_name': 'Vũ', 'last_name': 'Bị Cấm', 'phone': '0955555555'}


def get_or_create(model, lookup, defaults=None):
    """Idempotent create for demo data. Not for production request paths —
    seed scripts are allowed to touch models directly (see backfill_certificates.py)."""
    obj = model.objects.filter(**lookup).allow_filtering().first()
    if obj:
        return obj, False
    data = dict(lookup)
    data.update(defaults or {})
    return model.create(**data), True


class Command(BaseCommand):
    help = (
        "Seed full demo data across every LMS feature for two accounts:\n"
        f"  Space (teacher):   {SPACE_EMAIL} / {DEMO_PASSWORD}\n"
        f"  Consumer (student): {CONSUMER_EMAIL} / {DEMO_PASSWORD}\n\n"
        "Safe to re-run: entities with a natural unique key are reused; "
        "append-only children (logs, messages, xp history, notifications) "
        "are only seeded the first time their parent is created.\n\n"
        "Usage:\n"
        "  python manage.py seed_demo_data\n"
    )

    def handle(self, *args, **options):
        self.now = datetime.now()

        space = self._seed_space()
        consumer, classmates, pending_student, banned_student = self._seed_consumers()
        self._seed_addresses(space, consumer)
        self._seed_otp(consumer)
        self._seed_user_settings(space, consumer)

        classrooms, classroom_created = self._seed_classrooms(space)
        main_classroom = classrooms['fullstack']
        paid_classroom = classrooms['ielts']

        self._seed_memberships(
            classrooms, space, consumer, classmates, pending_student, banned_student,
            created=classroom_created,
        )
        self._seed_blacklist(space, banned_student)
        self._seed_activity_log(main_classroom, space, consumer, created=classroom_created)
        self._seed_teacher_contacts(space, [consumer] + classmates)

        folders, resources, resources_created = self._seed_resources(main_classroom, space, consumer)

        quizzes, quiz_created = self._seed_quizzes(space, main_classroom, resources)
        self._seed_quiz_logs(main_classroom, quizzes, consumer, created=quiz_created)

        certificate, collection, issued_cert, collection_created = self._seed_quiz_collection(
            space, main_classroom, quizzes, consumer,
        )

        exams, exam_created = self._seed_exams(space, main_classroom, quizzes, resources)
        self._seed_exam_progress(main_classroom, exams, consumer, quizzes, created=exam_created)

        rooms = self._seed_meeting_rooms(space, main_classroom, consumer)
        self._seed_chat(space, consumer, main_classroom)
        events, calendar_created = self._seed_calendar(space, main_classroom, consumer, exams)
        self._seed_notifications(space, consumer, created=calendar_created)
        self._seed_payment(space, consumer, paid_classroom)
        self._seed_portfolio(space, consumer)
        self._seed_ranking(consumer, classmates)
        self._seed_social(space, consumer, classmates, main_classroom, paid_classroom)
        self._seed_face(consumer)
        self._seed_ai(consumer, main_classroom)

        self.stdout.write(self.style.SUCCESS('\nDemo data seeded.'))
        self.stdout.write(f'  Space:    {SPACE_EMAIL} / {DEMO_PASSWORD}')
        self.stdout.write(f'  Consumer: {CONSUMER_EMAIL} / {DEMO_PASSWORD}')

    # ---------------------------------------------------------------- account

    def _seed_space(self):
        space, created = get_or_create(
            Space,
            {'email': SPACE_EMAIL},
            {
                'pid': generate_pid(),
                'password': make_password(DEMO_PASSWORD),
                'full_name': 'Nguyễn Văn Giảng',
                'name': 'LMS Demo Academy',
                'slug': 'lms-demo-academy',
                'description': 'Không gian giảng dạy trực tuyến cho lập trình, ngoại ngữ và khoa học dữ liệu.',
                'logo_url': 'https://picsum.photos/seed/lms-demo-logo/200',
                'cover_url': 'https://picsum.photos/seed/lms-demo-cover/1200/400',
                'hometown': 'Hà Nội',
                'date_of_birth': date(1990, 5, 20),
                'avatar_url': 'https://i.pravatar.cc/300?u=testspace',
                'learning_certificates': ['Chứng chỉ Nghiệp vụ Sư phạm', 'IELTS 8.0', 'AWS Certified Educator'],
                'contact_information': {'phone': '0901234567', 'facebook': 'facebook.com/lmsdemoacademy'},
                'is_verified': True,
                'is_active': True,
                'verified_at': self.now,
            },
        )
        self.stdout.write(self.style.SUCCESS(f'Space {"created" if created else "reused"}: {space.email}'))
        return space

    def _seed_consumer(self, data, role=ConsumerRole.STUDENT.value):
        consumer, created = get_or_create(
            Consumer,
            {'email': data['email']},
            {
                'pid': generate_pid(),
                'password': make_password(DEMO_PASSWORD),
                'username': data['email'].split('@')[0],
                'first_name': data['first_name'],
                'last_name': data['last_name'],
                'full_name': f"{data['first_name']} {data['last_name']}",
                'phone': data['phone'],
                'avatar_url': f"https://i.pravatar.cc/300?u={data['email']}",
                'role': role,
                'is_verified': True,
                'is_active': True,
                'verified_at': self.now,
            },
        )
        return consumer, created

    def _seed_consumers(self):
        consumer, created = self._seed_consumer({
            'email': CONSUMER_EMAIL, 'first_name': 'Trần', 'last_name': 'Thị Học Viên', 'phone': '0912345678',
        })
        self.stdout.write(self.style.SUCCESS(f'Consumer {"created" if created else "reused"}: {consumer.email}'))

        classmates = [self._seed_consumer(c)[0] for c in CLASSMATES]
        pending_student, _ = self._seed_consumer(PENDING_STUDENT)
        banned_student, _ = self._seed_consumer(BANNED_STUDENT)
        return consumer, classmates, pending_student, banned_student

    def _seed_addresses(self, space, consumer):
        get_or_create(
            Address,
            {'owner_id': consumer.uid, 'owner_type': 'consumer'},
            {
                'type': 'home', 'label': 'Nhà riêng',
                'line1': '123 Đường Cầu Giấy', 'line2': '',
                'province_code': 1, 'province_name': 'Thành phố Hà Nội',
                'ward_code': 4, 'ward_name': 'Phường Ba Đình',
            },
        )
        get_or_create(
            Address,
            {'owner_id': space.uid, 'owner_type': 'space'},
            {
                'type': 'work', 'label': 'Văn phòng',
                'line1': '45 Đường Lê Văn Việt', 'line2': 'Tầng 3',
                'province_code': 79, 'province_name': 'Thành phố Hồ Chí Minh',
                'ward_code': 26740, 'ward_name': 'Phường Bến Nghé',
            },
        )

    def _seed_otp(self, consumer):
        get_or_create(
            OTPRecord,
            {'user_uid': consumer.uid, 'user_type': 'consumer'},
            {
                'otp_code': '000000', 'email': consumer.email,
                'expires_at': self.now - timedelta(days=1),
                'is_otp_verified': True, 'is_reset_used': False,
            },
        )

    def _seed_user_settings(self, space, consumer):
        space_settings = {
            'space_profile': {'display_name': space.name, 'bio_visible': True},
            'security_config': {'two_factor': False, 'login_alerts': True},
            'classroom_defaults': {'max_students': 50, 'visibility_type': 'public'},
            'notification_prefs': {'email': True, 'push': True, 'student_joined': True},
        }
        for key, value in space_settings.items():
            get_or_create(
                UserSetting,
                {'user_id': space.uid, 'key': key},
                {'user_type': UserTypes.SPACE.value, 'value': json.dumps(value)},
            )

        consumer_settings = {
            'notification_prefs': {'email': True, 'push': True, 'grade_released': True},
            'theme': {'mode': 'light', 'accent_color': '#4f46e5'},
        }
        for key, value in consumer_settings.items():
            get_or_create(
                UserSetting,
                {'user_id': consumer.uid, 'key': key},
                {'user_type': UserTypes.CONSUMER.value, 'value': json.dumps(value)},
            )

    # -------------------------------------------------------------- classroom

    def _seed_classrooms(self, space):
        defs = {
            'fullstack': {
                'name': DEMO_CLASSROOM_NAME,
                'description': 'Học lập trình web từ HTML/CSS đến React và Node.js trong 12 tuần.',
                'max_students': 50, 'status': 'active', 'pricing_type': 'free', 'price_vnd': 0,
                'category': 'programming', 'visibility_type': 'public',
            },
            'ielts': {
                'name': 'IELTS Speaking Mastermind',
                'description': 'Luyện nói IELTS chuyên sâu theo nhóm nhỏ, cam kết đầu ra 7.0+.',
                'max_students': 30, 'status': 'active', 'pricing_type': 'paid', 'price_vnd': 1_500_000,
                'category': 'language', 'visibility_type': 'public',
            },
            'datascience': {
                'name': 'Data Science Foundations',
                'description': 'Nhập môn khoa học dữ liệu: Python, thống kê, machine learning cơ bản.',
                'max_students': 20, 'status': 'active', 'pricing_type': 'free', 'price_vnd': 0,
                'category': 'data', 'visibility_type': 'private',
            },
        }
        classrooms = {}
        any_created = False
        for slug, fields in defs.items():
            existing = [
                c for c in Classroom.objects.filter(teacher_id=space.uid, is_deleted=False)
                if c.name == fields['name']
            ]
            if existing:
                classrooms[slug] = existing[0]
                continue
            classrooms[slug] = Classroom.create(
                pid=generate_pid(), teacher_id=space.uid, **fields,
            )
            any_created = True
        self.stdout.write(self.style.SUCCESS(f"Classrooms ready: {[c.name for c in classrooms.values()]}"))
        return classrooms, any_created

    def _seed_memberships(self, classrooms, space, consumer, classmates, pending_student, banned_student, created):
        main = classrooms['fullstack']
        ielts = classrooms['ielts']
        datasci = classrooms['datascience']

        def ensure_member(classroom, member, member_type, role, status='approved', has_paid=False):
            existing = ClassroomMember.objects.filter(
                classroom_uid=classroom.uid, member_id=member.uid,
            ).allow_filtering().first()
            if existing:
                return existing
            return ClassroomMember.create(
                classroom_uid=classroom.uid, member_id=member.uid,
                member_type=member_type, member_name=getattr(member, 'full_name', space.full_name),
                member_avatar=member.avatar_url, role=role, status=status,
                is_verified=True, verified_at=self.now,
                has_paid=has_paid, paid_at=self.now if has_paid else None,
            )

        for classroom in (main, ielts, datasci):
            ensure_member(classroom, space, 'space', 'teacher')

        ensure_member(main, consumer, 'consumer', 'student')
        ensure_member(ielts, consumer, 'consumer', 'student', has_paid=True)
        ensure_member(datasci, consumer, 'consumer', 'student')

        for idx, mate in enumerate(classmates):
            ensure_member(main, mate, 'consumer', 'student')
            if idx < 2:
                ensure_member(ielts, mate, 'consumer', 'student', has_paid=(idx == 0))

        ensure_member(main, pending_student, 'consumer', 'student', status='pending')

    def _seed_blacklist(self, space, banned_student):
        get_or_create(
            TeacherBlacklist,
            {'teacher_id': space.uid, 'classroom_uid': GLOBAL_SENTINEL, 'consumer_uid': banned_student.uid},
            {'reason': 'Vi phạm nội quy lớp học nhiều lần.', 'added_by': space.uid},
        )

    def _seed_activity_log(self, classroom, space, consumer, created):
        if not created:
            return
        entries = [
            {'log_level': 'major', 'event_type': 'classroom_created', 'actor_id': space.uid,
             'actor_name': space.full_name, 'actor_role': 'teacher',
             'target_id': classroom.uid, 'target_name': classroom.name},
            {'log_level': 'detail', 'event_type': 'member_joined', 'actor_id': consumer.uid,
             'actor_name': consumer.full_name, 'actor_role': 'student',
             'target_id': classroom.uid, 'target_name': classroom.name},
            {'log_level': 'major', 'event_type': 'document_uploaded', 'actor_id': space.uid,
             'actor_name': space.full_name, 'actor_role': 'teacher',
             'target_name': 'Giáo trình HTML CSS.pdf'},
            {'log_level': 'major', 'event_type': 'exam_created', 'actor_id': space.uid,
             'actor_name': space.full_name, 'actor_role': 'teacher',
             'target_name': 'Kiểm tra giữa kỳ - HTML/CSS'},
            {'log_level': 'major', 'event_type': 'quiz_assigned', 'actor_id': space.uid,
             'actor_name': space.full_name, 'actor_role': 'teacher',
             'target_name': 'Trắc nghiệm HTML căn bản'},
        ]
        for offset, entry in enumerate(entries):
            ClassroomActivityLog.create(
                classroom_uid=classroom.uid,
                created_at=self.now - timedelta(days=len(entries) - offset, minutes=offset),
                metadata='{}',
                **entry,
            )

    def _seed_teacher_contacts(self, space, students):
        for idx, student in enumerate(students):
            get_or_create(
                TeacherContact,
                {'teacher_id': space.uid, 'consumer_uid': student.uid},
                {
                    'first_joined_at': self.now - timedelta(days=30 - idx),
                    'last_contact_at': self.now - timedelta(days=idx),
                    'last_contact_type': 'joined', 'contact_count': idx + 1,
                },
            )

    # -------------------------------------------------------------- resource

    def _seed_resources(self, classroom, space, consumer):
        folders = ResourceFolderSeedService().ensure_default_folders(classroom.uid, space.uid)

        def ensure_resource(name, file_type, url, size, owner_id, owner_type, folder_id=None):
            existing = Resource.objects.filter(
                owner_id=owner_id, owner_type=owner_type, name=name, is_deleted=False,
            ).allow_filtering().first()
            if existing:
                return existing, False
            return Resource.create(
                name=name, file_type=file_type, url=url, size=size,
                owner_id=owner_id, owner_type=owner_type, folder_id=folder_id, metadata={},
            ), True

        docs_pdf, c1 = ensure_resource(
            'Giáo trình HTML CSS.pdf', 'pdf',
            'https://lms-system-public.example.com/resources/giao-trinh-html-css.pdf',
            2_500_000, space.uid, 'space', folders['docs'].uid,
        )
        lecture_video, c2 = ensure_resource(
            'Video bài giảng buổi 1.mp4', 'video',
            'https://lms-system-public.example.com/resources/buoi-1.mp4',
            85_000_000, space.uid, 'space', folders['docs'].uid,
        )
        preview_image, c3 = ensure_resource(
            'Xem trước khóa học.jpg', 'jpg',
            'https://lms-system-public.example.com/resources/preview-course.jpg',
            350_000, space.uid, 'space', folders['preview'].uid,
        )
        submission_pdf, c4 = ensure_resource(
            'BaiTap_TranThiHocVien.pdf', 'pdf',
            'https://lms-system.example.com/resources/baitap-tranthihocvien.pdf',
            1_200_000, consumer.uid, 'consumer', None,
        )

        resources = {
            'docs_pdf': docs_pdf, 'lecture_video': lecture_video,
            'preview_image': preview_image, 'submission_pdf': submission_pdf,
        }
        return folders, resources, any([c1, c2, c3, c4])

    # ------------------------------------------------------------------ quiz

    def _seed_quizzes(self, space, classroom, resources):
        quiz1, c1 = get_or_create(
            Quiz, {'created_by': space.uid, 'title': 'Trắc nghiệm HTML căn bản'},
            {'resource_id': resources['docs_pdf'].uid, 'description': 'Kiểm tra kiến thức HTML cơ bản.',
             'questions_count': 3, 'status': 'published'},
        )
        quiz2, c2 = get_or_create(
            Quiz, {'created_by': space.uid, 'title': 'Trắc nghiệm CSS nâng cao'},
            {'description': 'Flexbox, Grid và responsive design.', 'questions_count': 2, 'status': 'published'},
        )

        if c1:
            questions1 = [
                {'question_text': 'Thẻ nào dùng để tạo liên kết trong HTML?',
                 'options': ['<link>', '<a>', '<href>', '<url>'],
                 'question_type': 'single_answer', 'correct_option_indices': [1],
                 'explanation': 'Thẻ <a> (anchor) dùng để tạo liên kết.', 'order': 0},
                {'question_text': 'Thuộc tính nào dùng để chỉ định đường dẫn ảnh trong thẻ <img>?',
                 'options': ['href', 'src', 'link', 'path'],
                 'question_type': 'single_answer', 'correct_option_indices': [1],
                 'explanation': 'Thuộc tính src chỉ định nguồn ảnh.', 'order': 1},
                {'question_text': 'Những thẻ nào sau đây là thẻ semantic HTML5?',
                 'options': ['<div>', '<header>', '<footer>', '<span>'],
                 'question_type': 'multi_answer', 'correct_option_indices': [1, 2],
                 'explanation': '<header> và <footer> là thẻ ngữ nghĩa HTML5.', 'order': 2},
            ]
            for q in questions1:
                QuizQuestion.create(quiz_id=quiz1.uid, **q)

        if c2:
            questions2 = [
                {'question_text': 'Thuộc tính CSS nào dùng để tạo layout linh hoạt theo hàng/cột?',
                 'options': ['display: block', 'display: flex', 'display: inline', 'position: fixed'],
                 'question_type': 'single_answer', 'correct_option_indices': [1],
                 'explanation': 'display: flex kích hoạt Flexbox layout.', 'order': 0},
                {'question_text': 'Đơn vị nào co giãn theo kích thước font gốc của trình duyệt?',
                 'options': ['px', 'rem', 'pt', 'cm'],
                 'question_type': 'single_answer', 'correct_option_indices': [1],
                 'explanation': 'rem tính theo font-size của thẻ root.', 'order': 1},
            ]
            for q in questions2:
                QuizQuestion.create(quiz_id=quiz2.uid, **q)

        get_or_create(
            QuizAssignment, {'quiz_id': quiz1.uid, 'classroom_id': classroom.uid},
            {'assigned_by': space.uid, 'time_limit_seconds': 600, 'max_attempts': 3,
             'shuffle_questions': True, 'shuffle_options': True, 'show_explanation': True,
             'passing_score_pct': 60},
        )

        quizzes = {'html_basics': quiz1, 'css_advanced': quiz2}
        return quizzes, (c1 or c2)

    def _seed_quiz_logs(self, classroom, quizzes, consumer, created):
        if not created:
            return
        quiz1 = quizzes['html_basics']
        questions = list(QuizQuestion.objects.filter(quiz_id=quiz1.uid))
        answers = {str(q.uid): str(q.correct_option_indices[0]) for q in questions}
        QuizLog.create(
            quiz_id=quiz1.uid, classroom_id=classroom.uid, student_id=consumer.uid,
            source='game', answers=answers, time_taken_seconds=280,
            submitted_at=self.now - timedelta(days=3),
            attempt_number=1, score=len(questions), total_questions=len(questions),
            score_pct=100, graded_at=self.now - timedelta(days=3),
        )

    def _seed_quiz_collection(self, space, classroom, quizzes, consumer):
        certificate, cert_created = get_or_create(
            Certificate, {'created_by': space.uid, 'name': 'Chứng chỉ hoàn thành Web Frontend'},
            {'description': 'Cấp cho học viên hoàn thành 100% bộ luyện thi Web Frontend.',
             'template_url': 'https://lms-system-public.example.com/certificates/web-frontend-template.pdf',
             'is_active': True},
        )
        collection, coll_created = get_or_create(
            QuizCollection, {'created_by': space.uid, 'title': 'Bộ luyện thi Web Frontend'},
            {'description': 'Gồm các bài trắc nghiệm HTML và CSS.', 'quiz_count': 2,
             'certificate_id': certificate.uid, 'status': 'published',
             'item_quiz_ids': [quizzes['html_basics'].uid, quizzes['css_advanced'].uid]},
        )
        get_or_create(
            QuizCollectionAssignment, {'collection_id': collection.uid, 'classroom_id': classroom.uid},
            {'assigned_by': space.uid},
        )
        issued_cert, issued_created = get_or_create(
            IssuedCertificate, {'student_id': consumer.uid, 'certificate_id': certificate.uid, 'collection_id': collection.uid},
            {'classroom_id': classroom.uid, 'issued_by': space.uid, 'issued_at': self.now - timedelta(days=1),
             'pdf_url': 'https://lms-system-public.example.com/certificates/issued/demo-consumer.pdf',
             'verification_code': secrets.token_hex(6).upper()},
        )
        return certificate, collection, issued_cert, coll_created

    # ------------------------------------------------------------------ exam

    def _seed_exams(self, space, classroom, quizzes, resources):
        exam1, c1 = get_or_create(
            Exam, {'classroom_id': classroom.uid, 'teacher_id': space.uid, 'title': 'Kiểm tra giữa kỳ - HTML/CSS'},
            {
                'content_type': 'quiz', 'ref_id': quizzes['html_basics'].uid,
                'meta': '{}', 'status': 'published', 'exam_type': 'quiz', 'exam_period': 'midterm',
                'max_grade': 10.0, 'camera_required': True, 'exam_mode': 'online',
                'duration_seconds': 1800, 'is_online_active': False,
                'opened_at': self.now - timedelta(days=3), 'late_threshold_seconds': 300,
                'max_visibility_breaks': 3, 'max_face_warnings': 2,
            },
        )
        exam2, c2 = get_or_create(
            Exam, {'classroom_id': classroom.uid, 'teacher_id': space.uid, 'title': 'Bài tập lớn: Landing Page cá nhân'},
            {
                'description': 'Nộp file HTML/CSS landing page hoàn chỉnh.',
                'content_type': 'file', 'ref_id': resources['docs_pdf'].uid,
                'meta': json.dumps({'url': resources['docs_pdf'].url, 'name': resources['docs_pdf'].name,
                                     'size': resources['docs_pdf'].size}),
                'status': 'published', 'exam_type': 'assignment', 'exam_period': 'regular',
                'max_grade': 10.0, 'camera_required': False, 'exam_mode': 'offline',
                'due_date': self.now + timedelta(days=7),
            },
        )
        exams = {'midterm_quiz': exam1, 'assignment': exam2}
        return exams, (c1 or c2)

    def _seed_exam_progress(self, classroom, exams, consumer, quizzes, created):
        if not created:
            return
        exam1 = exams['midterm_quiz']
        exam2 = exams['assignment']

        ExamSession.create(
            exam_id=exam1.uid, student_id=consumer.uid, token=secrets.token_hex(16),
            token_status='completed', token_expires_at=self.now - timedelta(days=3, hours=-1),
            started_at=self.now - timedelta(days=3), ends_at=self.now - timedelta(days=3, hours=-1),
            visibility_breaks_count=0, face_warnings_count=0,
            last_event_at=self.now - timedelta(days=3, hours=-1),
        )

        quiz_log = QuizLog.objects.filter(
            quiz_id=quizzes['html_basics'].uid, classroom_id=classroom.uid, student_id=consumer.uid,
        ).allow_filtering().first()

        ExamSubmission.create(
            exam_id=exam1.uid, classroom_id=classroom.uid, student_id=consumer.uid,
            submission_type='quiz', ref_id=quiz_log.uid if quiz_log else None,
            status='graded', submitted_at=self.now - timedelta(days=3),
            grade=10.0, max_grade=10.0, passed=True, feedback='Làm bài xuất sắc!',
            graded_by=None, graded_at=self.now - timedelta(days=3), grading_method='auto',
            is_effective=True,
        )
        ExamSubmission.create(
            exam_id=exam2.uid, classroom_id=classroom.uid, student_id=consumer.uid,
            submission_type='file', content='Landing page cá nhân - phiên bản 1',
            status='submitted', submitted_at=self.now - timedelta(hours=6),
            is_effective=True,
        )

        events = [
            ('audit', 'joined', {}), ('audit', 'submitted', {}),
            ('face', 'camera_open', {}), ('face', 'recognized', {'similarity': 0.94}),
        ]
        for kind, etype, data in events:
            ExamEventLog.create(
                exam_id=exam1.uid, student_id=consumer.uid, event_kind=kind, event_type=etype,
                event_data=json.dumps(data), created_at=self.now - timedelta(days=3),
            )

    # -------------------------------------------------------------- meeting

    def _seed_meeting_rooms(self, space, classroom, consumer):
        room1, c1 = get_or_create(
            MeetingRoom, {'classroom_uid': classroom.uid, 'title': 'Buổi học trực tuyến: Giới thiệu HTML'},
            {'description': 'Buổi học mở đầu khóa Lập trình Web Full-stack.',
             'host_id': space.uid, 'host_type': 'space', 'host_name': space.full_name,
             'status': 'ended', 'max_participants': 50, 'participant_count': 2,
             'started_at': self.now - timedelta(days=5), 'ended_at': self.now - timedelta(days=5, hours=-1)},
        )
        room2, c2 = get_or_create(
            MeetingRoom, {'classroom_uid': classroom.uid, 'title': 'Buổi học trực tuyến: Ôn tập JavaScript'},
            {'description': 'Buổi ôn tập sắp diễn ra.',
             'host_id': space.uid, 'host_type': 'space', 'host_name': space.full_name,
             'status': 'waiting', 'max_participants': 50, 'participant_count': 0},
        )

        if c1:
            MeetingRoomParticipant.create(
                room_uid=room1.uid, participant_id=space.uid, participant_type='space',
                participant_name=space.full_name, participant_avatar=space.avatar_url, role='host',
                joined_at=self.now - timedelta(days=5), left_at=self.now - timedelta(days=5, hours=-1),
            )
            MeetingRoomParticipant.create(
                room_uid=room1.uid, participant_id=consumer.uid, participant_type='consumer',
                participant_name=consumer.full_name, participant_avatar=consumer.avatar_url, role='participant',
                joined_at=self.now - timedelta(days=5), left_at=self.now - timedelta(days=5, hours=-1),
            )
        return {'ended': room1, 'waiting': room2}

    # ------------------------------------------------------------------ chat

    def _seed_chat(self, space, consumer, classroom):
        channel, c1 = get_or_create(
            Conversation, {'classroom_uid': classroom.uid, 'type': 'channel'},
            {'name': classroom.name, 'description': f'Kênh trao đổi của lớp {classroom.name}',
             'member_count': 2, 'created_by_id': space.uid},
        )
        if c1:
            ConversationMember.create(
                conversation_uid=channel.uid, member_id=space.uid, member_type='space',
                member_name=space.full_name, member_avatar=space.avatar_url,
            )
            ConversationMember.create(
                conversation_uid=channel.uid, member_id=consumer.uid, member_type='consumer',
                member_name=consumer.full_name, member_avatar=consumer.avatar_url,
            )
            msg1 = Message.create(
                conversation_uid=channel.uid, msg_type='text',
                content='Chào cả lớp! Buổi học tuần này sẽ học về Flexbox nhé.',
                sender_id=space.uid, sender_type='space', sender_name=space.full_name,
                created_at=self.now - timedelta(days=2),
            )
            Message.create(
                conversation_uid=channel.uid, msg_type='text',
                content='Dạ em cảm ơn thầy/cô ạ!',
                sender_id=consumer.uid, sender_type='consumer', sender_name=consumer.full_name,
                reply_to_uid=msg1.uid, created_at=self.now - timedelta(days=2, hours=-1),
            )
            Conversation.objects.filter(uid=channel.uid).update(
                last_msg_at=self.now - timedelta(days=2, hours=-1),
                last_msg_text='Dạ em cảm ơn thầy/cô ạ!', last_msg_sender=consumer.full_name,
            )

        uid_a, uid_b = sorted([space.uid, consumer.uid], key=str)
        pair_key = '|'.join(sorted([space.email, consumer.email]))
        direct, c2 = get_or_create(
            Conversation, {'type': 'direct', 'pair_key': pair_key},
            {'direct_a_id': uid_a, 'direct_b_id': uid_b, 'member_count': 2, 'created_by_id': consumer.uid},
        )
        if c2:
            ConversationMember.create(
                conversation_uid=direct.uid, member_id=space.uid, member_type='space',
                member_name=space.full_name, member_avatar=space.avatar_url,
            )
            ConversationMember.create(
                conversation_uid=direct.uid, member_id=consumer.uid, member_type='consumer',
                member_name=consumer.full_name, member_avatar=consumer.avatar_url,
            )
            msg = Message.create(
                conversation_uid=direct.uid, msg_type='text',
                content='Thầy/cô ơi, em nộp bài tập lớn hôm nay được không ạ?',
                sender_id=consumer.uid, sender_type='consumer', sender_name=consumer.full_name,
                created_at=self.now - timedelta(hours=5),
            )
            Message.create(
                conversation_uid=direct.uid, msg_type='text',
                content='Được nhé em, hạn nộp là cuối tuần này.',
                sender_id=space.uid, sender_type='space', sender_name=space.full_name,
                reply_to_uid=msg.uid, created_at=self.now - timedelta(hours=4),
            )
            Conversation.objects.filter(uid=direct.uid).update(
                last_msg_at=self.now - timedelta(hours=4),
                last_msg_text='Được nhé em, hạn nộp là cuối tuần này.', last_msg_sender=space.full_name,
            )

    # -------------------------------------------------------------- calendar

    def _seed_calendar(self, space, classroom, consumer, exams):
        class_event, c1 = get_or_create(
            CalendarEvent, {'classroom_id': classroom.uid, 'type': 'class', 'title': 'Buổi học: Flexbox & Grid'},
            {'description': 'Học layout hiện đại với CSS Flexbox và Grid.',
             'start_time': self.now + timedelta(days=2, hours=1), 'end_time': self.now + timedelta(days=2, hours=3),
             'space_id': space.uid, 'owner_id': space.uid},
        )
        exam_event, c2 = get_or_create(
            CalendarEvent, {'classroom_id': classroom.uid, 'type': 'exam', 'title': exams['midterm_quiz'].title},
            {'description': 'Kiểm tra giữa kỳ trực tuyến, bật camera bắt buộc.',
             'start_time': self.now - timedelta(days=3), 'end_time': self.now - timedelta(days=3, hours=-1),
             'space_id': space.uid, 'owner_id': space.uid},
        )
        deadline_event, c3 = get_or_create(
            CalendarEvent, {'classroom_id': classroom.uid, 'type': 'deadline', 'title': 'Hạn nộp bài tập lớn'},
            {'description': 'Hạn chót nộp landing page cá nhân.',
             'start_time': self.now + timedelta(days=7), 'end_time': self.now + timedelta(days=7, hours=1),
             'space_id': space.uid, 'owner_id': space.uid},
        )
        study_event, c4 = get_or_create(
            CalendarEvent, {'classroom_id': classroom.uid, 'type': 'study_session', 'title': 'Buổi tự học nhóm'},
            {'description': 'Ôn tập nhóm chuẩn bị thi cuối kỳ.',
             'start_time': self.now + timedelta(days=10), 'end_time': self.now + timedelta(days=10, hours=2),
             'space_id': space.uid, 'owner_id': space.uid},
        )

        created = any([c1, c2, c3, c4])
        if created:
            Attendance.create(
                event_id=exam_event.uid, user_id=consumer.uid, status='present',
                joined_at=self.now - timedelta(days=3), left_at=self.now - timedelta(days=3, hours=-1),
                date=date.today() - timedelta(days=3),
            )
            get_or_create(
                LeaveRequest, {'student_id': consumer.uid, 'space_id': space.uid, 'classroom_id': classroom.uid},
                {'event_id': class_event.uid, 'start_date': self.now + timedelta(days=2),
                 'end_date': self.now + timedelta(days=2, hours=3),
                 'reason': 'Xin nghỉ phép vì lý do sức khỏe.', 'status': 'pending'},
            )

        events = {'class': class_event, 'exam': exam_event, 'deadline': deadline_event, 'study_session': study_event}
        return events, created

    # ---------------------------------------------------------- notification

    def _seed_notifications(self, space, consumer, created):
        if not created:
            return
        consumer_notifs = [
            {'notify_type': 'exam_published', 'title': 'Bài kiểm tra mới',
             'content': 'Kiểm tra giữa kỳ - HTML/CSS đã được công bố.', 'is_read': True},
            {'notify_type': 'grade_released', 'title': 'Điểm đã được công bố',
             'content': 'Bạn đạt 10/10 điểm bài Kiểm tra giữa kỳ - HTML/CSS.', 'is_read': False},
            {'notify_type': 'certificate_issued', 'title': 'Chứng chỉ mới',
             'content': 'Bạn đã nhận chứng chỉ hoàn thành Web Frontend.', 'is_read': False},
        ]
        for n in consumer_notifs:
            NotificationLog.create(target_uid=consumer.uid, metadata='{}', **n)

        space_notifs = [
            {'notify_type': 'student_joined', 'title': 'Học viên mới',
             'content': 'Trần Thị Học Viên đã tham gia lớp Lập trình Web Full-stack.', 'is_read': True},
            {'notify_type': 'payment_received', 'title': 'Thanh toán mới',
             'content': 'Bạn vừa nhận thanh toán cho lớp IELTS Speaking Mastermind.', 'is_read': False},
            {'notify_type': 'exam_submitted', 'title': 'Bài nộp mới',
             'content': 'Trần Thị Học Viên vừa nộp bài Bài tập lớn: Landing Page cá nhân.', 'is_read': False},
        ]
        for n in space_notifs:
            NotificationLog.create(target_uid=space.uid, metadata='{}', **n)

    # -------------------------------------------------------------- payment

    def _seed_payment(self, space, consumer, paid_classroom):
        extra = json.dumps({
            'consumer_id': str(consumer.uid), 'resource_type': 'classroom',
            'resource_id': str(paid_classroom.uid), 'teacher_id': str(space.uid),
        })
        get_or_create(
            Payment, {'consumer_id': consumer.uid, 'order_id': f'DEMO-{paid_classroom.uid.hex[:12].upper()}'},
            {'teacher_id': space.uid, 'request_id': secrets.token_hex(8),
             'amount': paid_classroom.price_vnd, 'order_info': f'Thanh toán khóa học {paid_classroom.name}',
             'extra_data': extra, 'status': PaymentStatus.COMPLETED.value,
             'pay_url': '', 'result_code': 0, 'trans_id': 900000000001},
        )
        get_or_create(
            Payment, {'consumer_id': consumer.uid, 'order_id': f'DEMO-PENDING-{paid_classroom.uid.hex[:12].upper()}'},
            {'teacher_id': space.uid, 'request_id': secrets.token_hex(8),
             'amount': 500_000, 'order_info': 'Thanh toán chứng chỉ hoàn thành khóa học',
             'extra_data': extra, 'status': PaymentStatus.PENDING.value,
             'pay_url': 'https://payment.momo.vn/demo-pending', 'result_code': -1, 'trans_id': 0},
        )

    # ------------------------------------------------------------- portfolio

    def _seed_portfolio(self, space, consumer):
        def seed_keys(owner_id, owner_type, entries):
            for idx, (key, value, is_public) in enumerate(entries):
                get_or_create(
                    Portfolio, {'owner_id': owner_id, 'owner_type': owner_type, 'key': key},
                    {'value': json.dumps(value), 'is_public': is_public, 'display_order': idx},
                )

        seed_keys(space.uid, 'space', [
            ('bio', 'Giảng viên lập trình web với 8 năm kinh nghiệm đào tạo.', True),
            ('city', 'Hà Nội', True),
            ('country', 'Việt Nam', True),
            ('website', 'https://lmsdemoacademy.example.com', True),
            ('theme_color', '#4f46e5', True),
            ('profile_visibility', 'public', True),
            ('show_stats', True, True),
            ('show_classrooms', True, True),
            ('sections_order', ['intro', 'experience', 'certificate', 'course'], True),
            ('experience', [{'title': 'Giảng viên Full-stack', 'org': 'LMS Demo Academy', 'years': '2018-nay'}], True),
            ('certificate', [{'name': 'AWS Certified Educator', 'year': 2021}], True),
        ])

        seed_keys(consumer.uid, 'consumer', [
            ('bio', 'Sinh viên năm 3, đam mê lập trình web và AI.', True),
            ('city', 'Hà Nội', True),
            ('country', 'Việt Nam', True),
            ('major', 'Công nghệ thông tin', True),
            ('github', 'github.com/testconsumer', True),
            ('linkedin', 'linkedin.com/in/testconsumer', True),
            ('skills', ['HTML', 'CSS', 'JavaScript', 'React'], True),
            ('theme_color', '#22c55e', True),
            ('profile_visibility', 'public', True),
            ('show_certificates', True, True),
            ('show_activity', True, True),
            ('education', [{'school': 'Đại học Bách Khoa Hà Nội', 'major': 'Công nghệ thông tin', 'year': '2022-2026'}], True),
        ])

    # -------------------------------------------------------------- ranking

    def _seed_ranking(self, consumer, classmates):
        def award(student, event, classroom_id=None, days_ago=0):
            amount = XP_AMOUNTS[event]
            XPTransaction.create(
                student_id=student.uid, created_at=self.now - timedelta(days=days_ago),
                event_type=event.value, delta_xp=amount, classroom_id=classroom_id,
                description=XP_DESCRIPTIONS[event], metadata='{}',
            )
            return amount

        existing_xp = StudentXP.objects.filter(student_id=consumer.uid).first()
        if not existing_xp:
            total = 0
            total += award(consumer, XpEvent.CLASSROOM_JOINED, days_ago=20)
            total += award(consumer, XpEvent.CLASSROOM_JOINED, days_ago=15)
            total += award(consumer, XpEvent.CLASSROOM_JOINED, days_ago=10)
            for d in (3, 5, 8, 12):
                total += award(consumer, XpEvent.ATTENDANCE_PRESENT, days_ago=d)
            total += award(consumer, XpEvent.QUIZ_SUBMITTED, days_ago=3)
            total += award(consumer, XpEvent.QUIZ_PASSED, days_ago=3)
            total += award(consumer, XpEvent.QUIZ_PERFECT, days_ago=3)
            total += award(consumer, XpEvent.EXAM_SUBMITTED, days_ago=3)
            total += award(consumer, XpEvent.EXAM_PASSED, days_ago=3)
            total += award(consumer, XpEvent.COLLECTION_COMPLETED, days_ago=1)
            total += award(consumer, XpEvent.CERTIFICATE_ISSUED, days_ago=1)

            StudentXP.create(
                student_id=consumer.uid, total_xp=total, level=5,
                current_level_xp=65, next_level_xp=200, streak_days=5,
                last_active_date=date.today(), last_active_at=self.now,
                classrooms_joined_count=3, quizzes_passed_count=2, exams_passed_count=1,
                perfect_scores_count=1, certificates_count=1, attendance_count=4,
            )

            achievements = [
                {'achievement_code': 'first_classroom', 'title': 'Bước chân đầu tiên',
                 'description': 'Tham gia lớp học đầu tiên.', 'icon': 'flag',
                 'is_unlocked': True, 'unlocked_at': self.now - timedelta(days=20),
                 'target_value': 1, 'current_value': 1, 'progress_pct': 100},
                {'achievement_code': 'perfect_score', 'title': 'Điểm tuyệt đối',
                 'description': 'Đạt 100% điểm trong một bài kiểm tra.', 'icon': 'star',
                 'is_unlocked': True, 'unlocked_at': self.now - timedelta(days=3),
                 'target_value': 1, 'current_value': 1, 'progress_pct': 100},
                {'achievement_code': 'quiz_master', 'title': 'Bậc thầy trắc nghiệm',
                 'description': 'Hoàn thành 10 bài quiz.', 'icon': 'trophy',
                 'is_unlocked': False, 'target_value': 10, 'current_value': 2, 'progress_pct': 20},
                {'achievement_code': 'social_butterfly', 'title': 'Kết nối cộng đồng',
                 'description': 'Có 10 người theo dõi.', 'icon': 'users',
                 'is_unlocked': False, 'target_value': 10, 'current_value': 1, 'progress_pct': 10},
            ]
            for ach in achievements:
                StudentAchievement.create(student_id=consumer.uid, **ach)

        totals = [520, 275, 130]
        for mate, total in zip(classmates, totals):
            if StudentXP.objects.filter(student_id=mate.uid).first():
                continue
            StudentXP.create(
                student_id=mate.uid, total_xp=total, level=max(1, total // 100),
                current_level_xp=total % 100, next_level_xp=100, streak_days=total % 7,
                last_active_date=date.today(), last_active_at=self.now,
                classrooms_joined_count=1, quizzes_passed_count=total // 100,
                exams_passed_count=0, perfect_scores_count=0, certificates_count=0,
                attendance_count=total // 50,
            )

    # --------------------------------------------------------------- social

    def _seed_social(self, space, consumer, classmates, main_classroom, paid_classroom):
        def ensure_profile(owner_id, owner_type, avatar_url):
            get_or_create(
                SocialProfile, {'owner_id': owner_id},
                {'owner_type': owner_type, 'avatar_url': avatar_url, 'cover_url': '',
                 'posts_count': 1, 'followers_count': 0, 'following_count': 0},
            )

        ensure_profile(space.uid, 'space', space.avatar_url)
        ensure_profile(consumer.uid, 'consumer', consumer.avatar_url)
        if classmates:
            ensure_profile(classmates[0].uid, 'consumer', classmates[0].avatar_url)

        consumer_post, c1 = get_or_create(
            SocialPost, {'owner_id': consumer.uid, 'owner_type': 'consumer',
                         'content': 'Vừa hoàn thành khóa học Lập trình Web Full-stack! 🎉'},
            {'created_at': self.now - timedelta(days=1), 'owner_name': consumer.full_name,
             'owner_avatar': consumer.avatar_url, 'emotion': 'vui', 'visibility': 'public',
             'classroom_tags': [main_classroom.uid], 'likes_count': 2, 'comments_count': 1},
        )
        space_post, c2 = get_or_create(
            SocialPost, {'owner_id': space.uid, 'owner_type': 'space',
                         'content': 'Khai giảng lớp IELTS Speaking Mastermind — đăng ký ngay hôm nay!'},
            {'created_at': self.now - timedelta(days=2), 'owner_name': space.full_name,
             'owner_avatar': space.avatar_url, 'emotion': '', 'visibility': 'public',
             'classroom_tags': [paid_classroom.uid], 'likes_count': 1, 'comments_count': 0},
        )

        if c1 and classmates:
            mate = classmates[0]
            SocialPostComment.create(
                post_uid=consumer_post.uid, created_at=self.now - timedelta(hours=20),
                owner_id=mate.uid, owner_type='consumer', owner_name=mate.full_name,
                owner_avatar=mate.avatar_url, content='Chúc mừng bạn! Cố lên nhé 👏',
            )
            get_or_create(SocialPostLike, {'post_uid': consumer_post.uid, 'owner_id': mate.uid}, {'owner_type': 'consumer'})
            get_or_create(SocialPostLike, {'post_uid': consumer_post.uid, 'owner_id': space.uid}, {'owner_type': 'space'})

        if c2:
            get_or_create(SocialPostLike, {'post_uid': space_post.uid, 'owner_id': consumer.uid}, {'owner_type': 'consumer'})

        get_or_create(
            SocialFollow, {'uid': consumer.uid, 'followed_id': space.uid},
            {'follower_type': 'consumer', 'followed_type': 'space'},
        )
        if classmates:
            get_or_create(
                SocialFollow, {'uid': classmates[0].uid, 'followed_id': consumer.uid},
                {'follower_type': 'consumer', 'followed_type': 'consumer'},
            )

        get_or_create(ClassroomFavorite, {'consumer_uid': consumer.uid, 'classroom_uid': main_classroom.uid}, {})
        get_or_create(ClassroomFavorite, {'consumer_uid': consumer.uid, 'classroom_uid': paid_classroom.uid}, {})

    # ----------------------------------------------------------------- face

    def _seed_face(self, consumer):
        existing = FaceEmbedding.objects.filter(student_id=consumer.uid, is_active=True).allow_filtering().first()
        if existing:
            return
        dummy_vector = [round(((i * 37) % 200 - 100) / 100, 4) for i in range(512)]
        FaceEmbedding.create(
            student_id=consumer.uid, embedding_json=FaceEmbedding.set_embedding(dummy_vector),
            enrolled_at=self.now - timedelta(days=10), is_active=True,
        )

    # ------------------------------------------------------------------- ai

    def _seed_ai(self, consumer, classroom):
        existing = AIConversationSession.objects.filter(
            user_id=consumer.uid, classroom_id=classroom.uid,
        ).allow_filtering().first()
        if existing:
            return
        session = AIConversationSession.create(
            user_id=consumer.uid, classroom_id=classroom.uid, title='Hỏi đáp bài tập HTML',
            created_at=self.now - timedelta(hours=2), updated_at=self.now - timedelta(hours=2),
        )
        ai_repo = AIMessageRepository()
        ai_repo.add_user_message(str(session.session_id), 'Sự khác nhau giữa thẻ <div> và <span> là gì?', str(consumer.uid), consumer.full_name)
        ai_repo.add_ai_message(
            str(session.session_id),
            '<div> là phần tử block-level, chiếm toàn bộ chiều rộng và luôn xuống dòng. '
            '<span> là phần tử inline, chỉ chiếm đúng phần nội dung bên trong và không xuống dòng.',
        )
