from django.urls import path
from features.course.exam.viewsets import SpaceAssignmentViewSet

urlpatterns = [
    path('', SpaceAssignmentViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('<uuid:uid>/', SpaceAssignmentViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'update', 'delete': 'destroy'})),
    path('<uuid:exam_uid>/submissions/', SpaceAssignmentViewSet.as_view({'get': 'list_submissions'})),
    path('<uuid:exam_uid>/submissions/ai-grade/', SpaceAssignmentViewSet.as_view({'post': 'ai_grade_exam_submissions'})),
    path('submissions/<uuid:submission_uid>/', SpaceAssignmentViewSet.as_view({'get': 'get_submission'})),
    path('submissions/<uuid:submission_uid>/grade/', SpaceAssignmentViewSet.as_view({'patch': 'grade_submission'})),
    path('submissions/<uuid:submission_uid>/ai-grade/', SpaceAssignmentViewSet.as_view({'post': 'ai_grade_submission'})),
]
