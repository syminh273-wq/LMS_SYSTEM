from django.urls import path, include
from rest_framework.routers import DefaultRouter
from features.course.classroom.viewsets import ClassroomViewSet, ClassroomMemberViewSet
from features.course.classroom.viewsets.classroom_blacklist_viewset import (
    ClassroomBlacklistView,
    ClassroomBlacklistDetailView,
)

router = DefaultRouter()
router.register(r'', ClassroomViewSet, basename='classroom')

_member = ClassroomMemberViewSet
_classroom = ClassroomViewSet

urlpatterns = [
    path('', include(router.urls)),
    # DELETE /classrooms/<uid>/docs/<resource_uid>/
    path('<str:uid>/docs/<str:resource_uid>/',
         _classroom.as_view({'delete': 'docs_delete'}),
         name='classroom-docs-delete'),
    # POST /classrooms/<uid>/ask-stream/  — SSE streaming AI bot (supports audio param for STT)
    path('<str:uid>/ask-stream/',
         _classroom.as_view({'post': 'ask_stream'}),
         name='classroom-ask-stream'),
    # POST /classrooms/<uid>/tts/  — Text-to-Speech, returns MP3
    path('<str:uid>/tts/',
         _classroom.as_view({'post': 'tts'}),
         name='classroom-tts'),
    # Nested member routes: /classrooms/<classroom_uid>/members/
    path('<str:classroom_uid>/members/',
         _member.as_view({'get': 'list'}),
         name='classroom-members-list'),
    path('<str:classroom_uid>/members/join/',
         _member.as_view({'post': 'join'}),
         name='classroom-members-join'),
    path('<str:classroom_uid>/members/leave/',
         _member.as_view({'post': 'leave'}),
         name='classroom-members-leave'),
    path('<str:classroom_uid>/members/<str:member_id>/approve/',
         _member.as_view({'post': 'approve'}),
         name='classroom-members-approve'),
    path('<str:classroom_uid>/members/<str:member_id>/reject/',
         _member.as_view({'delete': 'reject'}),
         name='classroom-members-reject'),
    path('<str:classroom_uid>/members/<str:member_id>/kick/',
         _member.as_view({'delete': 'kick'}),
         name='classroom-members-kick'),
    path('<str:classroom_uid>/members/<str:member_id>/submissions/',
         _member.as_view({'get': 'student_submissions'}),
         name='classroom-members-submissions'),
    # Blacklist routes: /classrooms/<uid>/blacklist/
    path('<str:uid>/blacklist/',
         ClassroomBlacklistView.as_view(),
         name='classroom-blacklist'),
    path('<str:uid>/blacklist/<str:consumer_uid>/',
         ClassroomBlacklistDetailView.as_view(),
         name='classroom-blacklist-detail'),
]
