from django.urls import path, include
from rest_framework.routers import DefaultRouter
from features.course.classroom.viewsets import ConsumerClassroomViewSet
from features.course.exam.viewsets import ConsumerExamViewSet
from features.course.exam.viewsets.consumer_exam_event_viewset import (
    ConsumerExamEventViewSet,
)
from features.course.viewsets import ConsumerCourseViewSet

router = DefaultRouter()
router.register(r'classrooms', ConsumerClassroomViewSet, basename='consumer-classroom')
router.register(r'courses', ConsumerCourseViewSet, basename='consumer-course')

_consumer_classroom = ConsumerClassroomViewSet

urlpatterns = [
    path('classrooms/<uuid:uid>/exams/', ConsumerExamViewSet.as_view({'get': 'list_classroom_exams'})),
    path('exams/<uuid:exam_uid>/questions/', ConsumerExamViewSet.as_view({'get': 'get_quiz_questions'})),
    path('exams/<uuid:exam_uid>/submissions/', ConsumerExamViewSet.as_view({'post': 'submit'})),
    path('exams/<uuid:exam_uid>/submissions/me/', ConsumerExamViewSet.as_view({'get': 'my_submission'})),
    path('exam-sessions/<str:token>/', ConsumerExamViewSet.as_view({'get': 'join_session'})),
    path('exam-sessions/<uuid:session_uid>/events/', ConsumerExamEventViewSet.as_view({'post': 'record_event'})),
    path('exam-sessions/<uuid:session_uid>/audit-log/me/', ConsumerExamViewSet.as_view({'get': 'my_audit_log'})),
    path('exams/<uuid:exam_uid>/sessions/me/', ConsumerExamViewSet.as_view({'get': 'my_session'})),
    # SSE streaming AI bot (manual route — pk used as positional kwarg from router)
    path('classrooms/<str:pk>/ask-stream/',
         _consumer_classroom.as_view({'post': 'ask_stream'}),
         name='consumer-classroom-ask-stream'),
    path('', include(router.urls)),
    path('meeting-rooms/', include('features.course.meeting_room.urls')),
]
