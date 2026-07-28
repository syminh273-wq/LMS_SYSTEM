from django.urls import path
from features.course.exam.viewsets import SpaceExamViewSet

urlpatterns = [
    path('', SpaceExamViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('<uuid:uid>/', SpaceExamViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'})),
    path('<uuid:uid>/open-online/', SpaceExamViewSet.as_view({'post': 'open_online'})),
    path('<uuid:uid>/close-online/', SpaceExamViewSet.as_view({'post': 'close_online'})),
    path('<uuid:uid>/online-sessions/', SpaceExamViewSet.as_view({'get': 'list_online_sessions'})),
    path('<uuid:exam_uid>/submissions/', SpaceExamViewSet.as_view({'get': 'list_submissions'})),
    path('<uuid:exam_uid>/submissions/ai-grade/', SpaceExamViewSet.as_view({'post': 'ai_grade_exam_submissions'})),
    path('submissions/<uuid:submission_uid>/', SpaceExamViewSet.as_view({'get': 'get_submission'})),
    path('submissions/<uuid:submission_uid>/grade/', SpaceExamViewSet.as_view({'patch': 'grade_submission'})),
    path('submissions/<uuid:submission_uid>/ai-grade/', SpaceExamViewSet.as_view({'post': 'ai_grade_submission'})),
    path('submissions/<uuid:submission_uid>/audit-log/overview/', SpaceExamViewSet.as_view({'get': 'audit_log_overview'})),
    path('submissions/<uuid:submission_uid>/audit-log/details/', SpaceExamViewSet.as_view({'get': 'audit_log_details'})),
    path('submissions/<uuid:submission_uid>/audit-log/answers/', SpaceExamViewSet.as_view({'get': 'audit_log_answers'})),
    path('submissions/<uuid:submission_uid>/effectiveness/', SpaceExamViewSet.as_view({'patch': 'set_effectiveness'})),
]
