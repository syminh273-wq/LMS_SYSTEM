from django.urls import path
from features.course.exam.viewsets import (
    SpaceExamSubmissionDetailViewSet,
    SpaceExamSubmissionGradeViewSet,
    SpaceExamSubmissionViewSet,
    SpaceExamViewSet,
)

urlpatterns = [
    path('', SpaceExamViewSet.as_view()),
    path('<uuid:exam_uid>/submissions/', SpaceExamSubmissionViewSet.as_view()),
    path('submissions/<uuid:submission_uid>/', SpaceExamSubmissionDetailViewSet.as_view()),
    path('submissions/<uuid:submission_uid>/grade/', SpaceExamSubmissionGradeViewSet.as_view()),
    path('<uuid:uid>/', SpaceExamViewSet.as_view()),
]
