from django.core.management.base import BaseCommand
from django.conf import settings

from cassandra.cqlengine import management
from cassandra.cqlengine.models import Model as CqlModel
from cassandra.cqlengine.management import drop_table, sync_table, create_keyspace_simple
from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster
from django_cassandra_engine.models import DjangoCassandraModel

from features.social.models import (
    SocialPost, SocialPostLike, SocialPostComment, SocialFollow,
    SocialProfile, ClassroomFavorite,
)
from features.chat.models import Conversation, ConversationMember, Message
from features.account.consumer.models.address import Address
from features.account.consumer.models.consumer import Consumer
from features.account.space.models.space import Space
from features.account.otp.models.otp_record import OTPRecord
from features.account.user_setting.models.user_setting import UserSetting
from features.ai.models.ai_conversation_session import AIConversationSession
from features.calendar.models.attendance import Attendance
from features.calendar.models.calendar_event import CalendarEvent
from features.calendar.models.leave_request import LeaveRequest
from features.course.classroom.models.classroom import Classroom
from features.course.classroom.models.classroom_activity_log import ClassroomActivityLog
from features.course.classroom.models.classroom_member import ClassroomMember
from features.course.classroom.models.teacher_blacklist import TeacherBlacklist
from features.course.classroom.models.teacher_contact import TeacherContact
from features.course.exam.models.exam import Exam
from features.course.exam.models.exam_event_log import ExamEventLog
from features.course.exam.models.exam_session import ExamSession
from features.course.exam.models.exam_submission import ExamSubmission
from features.course.meeting_room.models.meeting_room import MeetingRoom
from features.course.meeting_room.models.meeting_room_participant import MeetingRoomParticipant
from features.face.models.face_embedding import FaceEmbedding
from features.notification.models.notification_log import NotificationLog
from features.payment.models.payment import Payment
from features.portfolio.models.portfolio import Portfolio
from features.quiz.models.quiz import Quiz
from features.quiz.models.quiz_assignment import QuizAssignment
from features.quiz.models.quiz_log import QuizLog
from features.quiz.models.quiz_question import QuizQuestion
from features.quiz_collection.models.certificate import Certificate
from features.quiz_collection.models.issued_certificate import IssuedCertificate
from features.quiz_collection.models.quiz_collection import QuizCollection
from features.quiz_collection.models.quiz_collection_assignment import QuizCollectionAssignment
from features.ranking.models.achievement import StudentAchievement
from features.ranking.models.student_xp import StudentXP
from features.ranking.models.xp_transaction import XPTransaction
from features.resource.models.resource import Resource
from features.resource.models.resource_folder import ResourceFolder
from core.models.social_account import SocialAccount


def _cassandra_cfg():
    return settings.DATABASES.get('default', {})


def _make_cluster(hosts, cfg):
    """Build a Cluster with auth_provider when credentials are configured."""
    kwargs = {
        'contact_points': hosts if isinstance(hosts, list) else [hosts],
    }
    user = (cfg.get('USER') or cfg.get('USERNAME') or '').strip()
    pwd = cfg.get('PASSWORD') or ''
    if user:
        kwargs['auth_provider'] = PlainTextAuthProvider(username=user, password=pwd)
    return Cluster(**kwargs)


def _is_auth_error(exc) -> bool:
    msg = str(exc).lower()
    return (
        'authenticationfailed' in msg
        or 'unable to connect' in msg
        or 'requires authentication' in msg
    )


def _add_missing_columns(model, keyspace, hosts, cfg, stdout):
    """ALTER TABLE to add columns that exist on the model but not in the schema."""
    try:
        cluster = _make_cluster(hosts, cfg)
        session = cluster.connect(keyspace)
        rows = session.execute(
            "SELECT column_name FROM system_schema.columns "
            "WHERE keyspace_name=%s AND table_name=%s",
            (keyspace, model.__table_name__)
        )
        existing = {r.column_name for r in rows}
        cluster.shutdown()
    except Exception as e:
        if _is_auth_error(e):
            stdout.write(f'  AUTH FAIL: cannot connect to Cassandra — {e}')
        else:
            stdout.write(f'  could not read schema for {model.__table_name__}: {e}')
        return

    type_map = {
        'UUID':        'uuid',
        'Text':        'text',
        'Integer':     'int',
        'DateTime':    'timestamp',
        'Boolean':     'boolean',
        'Float':       'float',
        'Double':      'double',
        'BigInt':      'bigint',
        'TimeUUID':    'timeuuid',
    }

    from cassandra.cqlengine import columns as c_cols
    for name, col in model._columns.items():
        if name in existing:
            continue
        if getattr(col, 'primary_key', False) or getattr(col, 'partition_key', False):
            continue
        cql_type = type_map.get(type(col).__name__)
        if cql_type is None:
            continue
        if isinstance(col, c_cols.List):
            inner = type_map.get(type(col.value_type).__name__, 'text')
            cql_type = f'list<{inner}>'
        elif isinstance(col, c_cols.Set):
            inner = type_map.get(type(col.value_type).__name__, 'text')
            cql_type = f'set<{inner}>'
        elif isinstance(col, c_cols.Map):
            k = type_map.get(type(col.key_type).__name__, 'text')
            v = type_map.get(type(col.value_type).__name__, 'text')
            cql_type = f'map<{k},{v}>'

        try:
            cluster = _make_cluster(hosts, cfg)
            session = cluster.connect(keyspace)
            session.execute(
                f'ALTER TABLE {model.__table_name__} ADD {name} {cql_type}'
            )
            cluster.shutdown()
            stdout.write(f'  + added column {name} {cql_type} to {model.__table_name__}')
        except Exception as e:
            stdout.write(f'  ! failed to add {name} to {model.__table_name__}: {e}')


def _drop_extra_columns(model, keyspace, hosts, cfg, stdout):
    """ALTER TABLE DROP columns that exist in DB but not on the model.
    Cassandra supports DROP COLUMN since 2.2 — non-PK columns only."""
    try:
        cluster = _make_cluster(hosts, cfg)
        session = cluster.connect(keyspace)
        rows = session.execute(
            "SELECT column_name FROM system_schema.columns "
            "WHERE keyspace_name=%s AND table_name=%s",
            (keyspace, model.__table_name__)
        )
        existing = {r.column_name for r in rows}
        cluster.shutdown()
    except Exception as e:
        if _is_auth_error(e):
            stdout.write(f'  AUTH FAIL: cannot connect to Cassandra — {e}')
            return
        stdout.write(f'  could not read schema for {model.__table_name__}: {e}')
        return

    model_columns = set()
    for col in model._columns.values():
        model_columns.add(col.column_name)

    for col_name in existing - model_columns:
        if col_name in ('created_at', 'updated_at', 'is_deleted', 'deleted_at'):
            continue
        try:
            cluster = _make_cluster(hosts, cfg)
            session = cluster.connect(keyspace)
            session.execute(
                f'ALTER TABLE {model.__table_name__} DROP {col_name}'
            )
            cluster.shutdown()
            stdout.write(f'  - dropped column {col_name} from {model.__table_name__}')
        except Exception as e:
            stdout.write(f'  ! failed to drop {col_name} from {model.__table_name__}: {e}')


class Command(BaseCommand):
    help = 'Sync all Cassandra tables (create if not exists)'

    def handle(self, *args, **options):
        cfg = _cassandra_cfg()
        keyspace = cfg.get('NAME')
        hosts = cfg.get('HOST', '127.0.0.1')

        # Allow sync_table() to accept DjangoCassandraModel subclasses.
        # cqlengine's _sync_table does `issubclass(model, Model)`; without this
        # patch every model raises "Models must be derived from base Model."
        management.Model = (CqlModel, DjangoCassandraModel)

        # Ensure keyspace exists
        try:
            if keyspace and hosts:
                create_keyspace_simple(keyspace, replication_factor=1)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'keyspace check: {e}'))

        models = [
            # core
            ('core.SocialAccount',                   SocialAccount),

            # account
            ('account.Consumer',                     Consumer),
            ('account.Space',                        Space),
            ('account.Address',                      Address),
            ('account.OTPRecord',                    OTPRecord),
            ('account.UserSetting',                  UserSetting),

            # ai
            ('ai.AIConversationSession',             AIConversationSession),

            # calendar
            ('calendar.CalendarEvent',               CalendarEvent),
            ('calendar.Attendance',                  Attendance),
            ('calendar.LeaveRequest',                LeaveRequest),

            # chat
            ('chat.Conversation',                    Conversation),
            ('chat.ConversationMember',              ConversationMember),
            ('chat.Message',                         Message),

            # course
            ('course.Classroom',                     Classroom),
            ('course.ClassroomMember',               ClassroomMember),
            ('course.ClassroomActivityLog',          ClassroomActivityLog),
            ('course.TeacherBlacklist',              TeacherBlacklist),
            ('course.TeacherContact',                TeacherContact),
            ('course.Exam',                          Exam),
            ('course.ExamSession',                   ExamSession),
            ('course.ExamSubmission',                ExamSubmission),
            ('course.ExamEventLog',                  ExamEventLog),
            ('course.MeetingRoom',                   MeetingRoom),
            ('course.MeetingRoomParticipant',        MeetingRoomParticipant),

            # face
            ('face.FaceEmbedding',                   FaceEmbedding),

            # notification
            ('notification.NotificationLog',         NotificationLog),

            # payment
            ('payment.Payment',                      Payment),

            # portfolio
            ('portfolio.Portfolio',                  Portfolio),

            # quiz
            ('quiz.Quiz',                            Quiz),
            ('quiz.QuizQuestion',                    QuizQuestion),
            ('quiz.QuizAssignment',                  QuizAssignment),
            ('quiz.QuizLog',                         QuizLog),

            # quiz_collection
            ('quiz_collection.QuizCollection',       QuizCollection),
            ('quiz_collection.QuizCollectionAssignment', QuizCollectionAssignment),
            ('quiz_collection.Certificate',          Certificate),
            ('quiz_collection.IssuedCertificate',    IssuedCertificate),

            # ranking
            ('ranking.StudentXP',                    StudentXP),
            ('ranking.XPTransaction',                XPTransaction),
            ('ranking.StudentAchievement',           StudentAchievement),

            # resource
            ('resource.Resource',                    Resource),
            ('resource.ResourceFolder',              ResourceFolder),

            # social
            ('social.UserProfile',                   SocialProfile),
            ('social.SocialPost',                    SocialPost),
            ('social.SocialPostLike',                SocialPostLike),
            ('social.SocialPostComment',             SocialPostComment),
            ('social.SocialFollow',                  SocialFollow),
            ('social.ClassroomFavorite',             ClassroomFavorite),
        ]

        for label, model in models:
            try:
                sync_table(model)
                self.stdout.write(self.style.SUCCESS(f'OK   {label}'))
            except Exception as e:
                msg = str(e)
                if 'already exists' in msg.lower() or 'unconfigured table' in msg.lower():
                    self.stdout.write(f'SKIP {label} ({msg[:60]})')
                elif _is_auth_error(e):
                    self.stdout.write(self.style.ERROR(f'AUTH FAIL {label}: {e}'))
                else:
                    self.stdout.write(self.style.ERROR(f'FAIL {label}: {e}'))

            try:
                _add_missing_columns(model, keyspace, hosts, cfg, self.stdout)
            except Exception as e:
                self.stdout.write(f'  column check failed for {label}: {e}')

            try:
                _drop_extra_columns(model, keyspace, hosts, cfg, self.stdout)
            except Exception as e:
                self.stdout.write(f'  drop extra columns failed for {label}: {e}')

        self.stdout.write(self.style.SUCCESS('Sync done.'))


