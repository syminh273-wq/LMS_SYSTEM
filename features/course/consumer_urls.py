from django.urls import path, include
from rest_framework.routers import DefaultRouter
from features.course.classroom.viewsets import ConsumerClassroomViewSet
from features.course.exam.viewsets import (
    ConsumerClassroomExamViewSet,
    ConsumerExamSubmissionViewSet,
    ConsumerMyExamSubmissionViewSet,
)

router = DefaultRouter()
router.register(r'classrooms', ConsumerClassroomViewSet, basename='consumer-classroom')

urlpatterns = [
    path('classrooms/<uuid:uid>/exams/', ConsumerClassroomExamViewSet.as_view()),
    path('exams/<uuid:exam_uid>/submissions/', ConsumerExamSubmissionViewSet.as_view()),
    path('exams/<uuid:exam_uid>/submissions/me/', ConsumerMyExamSubmissionViewSet.as_view()),
    path('', include(router.urls)),
    path('meeting-rooms/', include('features.course.meeting_room.urls')),
]
