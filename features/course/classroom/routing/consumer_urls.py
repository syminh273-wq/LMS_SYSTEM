from django.urls import path, include
from rest_framework.routers import DefaultRouter
from features.course.classroom.viewsets import ConsumerClassroomViewSet, ConsumerClassroomAIViewSet

router = DefaultRouter()
router.register(r'classrooms', ConsumerClassroomViewSet, basename='consumer-classroom')

urlpatterns = [
    path('classrooms/<str:pk>/ask/',
         ConsumerClassroomAIViewSet.as_view({'post': 'ask'}),
         name='consumer-classroom-ask'),
    path('classrooms/<str:pk>/ask-stream/',
         ConsumerClassroomAIViewSet.as_view({'post': 'ask_stream'}),
         name='consumer-classroom-ask-stream'),
    path('classrooms/<str:pk>/active-session/',
         ConsumerClassroomAIViewSet.as_view({'get': 'active_session'}),
         name='consumer-classroom-active-session'),
    path('classrooms/<str:pk>/ai-session/',
         ConsumerClassroomAIViewSet.as_view({'post': 'ai_session'}),
         name='consumer-classroom-ai-session'),
    path('classrooms/<str:pk>/ai-sessions/',
         ConsumerClassroomAIViewSet.as_view({'get': 'ai_sessions'}),
         name='consumer-classroom-ai-sessions'),
    path('classrooms/<str:pk>/ai-session/history/',
         ConsumerClassroomAIViewSet.as_view({'get': 'ai_session_history'}),
         name='consumer-classroom-ai-session-history'),
    path('', include(router.urls)),
]
