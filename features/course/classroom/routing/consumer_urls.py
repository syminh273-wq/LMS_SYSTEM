from django.urls import path, include
from rest_framework.routers import DefaultRouter
from features.course.classroom.viewsets import ConsumerClassroomViewSet

router = DefaultRouter()
router.register(r'classrooms', ConsumerClassroomViewSet, basename='consumer-classroom')

urlpatterns = [
    path('classrooms/<str:pk>/ask-stream/',
         ConsumerClassroomViewSet.as_view({'post': 'ask_stream'}),
         name='consumer-classroom-ask-stream'),
    path('', include(router.urls)),
]
