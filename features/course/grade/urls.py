from django.urls import path

from features.course.grade.viewsets import (
    SpaceAIGradeViewSet,
    SpaceSubmissionGradeHistoryViewSet,
    SpaceTeacherGradeViewSet,
)


urlpatterns = [
    path("submissions/<uuid:submission_uid>/", SpaceSubmissionGradeHistoryViewSet.as_view()),
    path("submissions/<uuid:submission_uid>/ai/", SpaceAIGradeViewSet.as_view()),
    path("submissions/<uuid:submission_uid>/teacher/", SpaceTeacherGradeViewSet.as_view()),
]
