from django.urls import path
from features.course.exam.viewsets import ConsumerExamViewSet, ConsumerAssignmentViewSet
from features.course.exam.viewsets.consumer_exam_event_viewset import ConsumerExamEventViewSet

urlpatterns = [
    path('classrooms/<uuid:uid>/exams/', ConsumerExamViewSet.as_view({'get': 'list_classroom_exams'})),
    path('classrooms/<uuid:uid>/assignments/', ConsumerAssignmentViewSet.as_view({'get': 'list_classroom_assignments'})),
    path('assignments/<uuid:exam_uid>/submissions/', ConsumerAssignmentViewSet.as_view({'post': 'submit'})),
    path('assignments/<uuid:exam_uid>/submissions/me/', ConsumerAssignmentViewSet.as_view({'get': 'my_submission'})),
    path('exams/<uuid:exam_uid>/', ConsumerExamViewSet.as_view({'get': 'retrieve'})),
    path('exams/<uuid:exam_uid>/questions/', ConsumerExamViewSet.as_view({'get': 'get_quiz_questions'})),
    path('exams/<uuid:exam_uid>/submissions/', ConsumerExamViewSet.as_view({'post': 'submit'})),
    path('exams/<uuid:exam_uid>/submissions/me/', ConsumerExamViewSet.as_view({'get': 'my_submission'})),
    path('exam-sessions/<str:token>/', ConsumerExamViewSet.as_view({'get': 'join_session'})),
    path('exam-sessions/<uuid:session_uid>/events/', ConsumerExamEventViewSet.as_view({'post': 'record_event'})),
    path('exam-sessions/<uuid:session_uid>/audit-log/me/', ConsumerExamViewSet.as_view({'get': 'my_audit_log'})),
    path('exams/<uuid:exam_uid>/sessions/me/', ConsumerExamViewSet.as_view({'get': 'my_session'})),
]
