from django.urls import path, include
from rest_framework.routers import DefaultRouter
from features.course.classroom.viewsets import ConsumerClassroomViewSet

router = DefaultRouter()
router.register(r'classrooms', ConsumerClassroomViewSet, basename='consumer-classroom')

urlpatterns = [
    path('', include(router.urls)),
]
