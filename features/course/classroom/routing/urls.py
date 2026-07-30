from django.urls import path, include
from rest_framework.routers import DefaultRouter
from features.course.classroom.viewsets import SpaceClassroomViewSet, SpaceClassroomMemberViewSet, SpaceClassroomAIViewSet
from features.course.classroom.views.space_classroom_blacklist_views import (
    SpaceClassroomBlacklistView,
    SpaceClassroomBlacklistDetailView,
)

router = DefaultRouter()
router.register(r'', SpaceClassroomViewSet, basename='classroom')

urlpatterns = [
    path('', include(router.urls)),
    # POST upload doc / GET list docs /classrooms/<uid>/docs/
    path('<str:uid>/docs/',
         SpaceClassroomViewSet.as_view({'post': 'docs_upload', 'get': 'docs_list'}),
         name='classroom-docs'),
    # DELETE /classrooms/<uid>/docs/<resource_uid>/
    path('<str:uid>/docs/<str:resource_uid>/',
         SpaceClassroomViewSet.as_view({'delete': 'docs_delete'}),
         name='classroom-docs-delete'),
    # AI Q&A bot — served by SpaceClassroomAIViewSet
    path('<str:uid>/ask/',
         SpaceClassroomAIViewSet.as_view({'post': 'ask'}),
         name='classroom-ask'),
    path('<str:uid>/ask-stream/',
         SpaceClassroomAIViewSet.as_view({'post': 'ask_stream'}),
         name='classroom-ask-stream'),
    path('<str:uid>/active-session/',
         SpaceClassroomAIViewSet.as_view({'get': 'active_session'}),
         name='classroom-active-session'),
    path('<str:uid>/ai-session/',
         SpaceClassroomAIViewSet.as_view({'post': 'ai_session'}),
         name='classroom-ai-session'),
    path('<str:uid>/ai-sessions/',
         SpaceClassroomAIViewSet.as_view({'get': 'ai_sessions'}),
         name='classroom-ai-sessions'),
    path('<str:uid>/ai-session/history/',
         SpaceClassroomAIViewSet.as_view({'get': 'ai_session_history'}),
         name='classroom-ai-session-history'),
    path('<str:classroom_uid>/members/', SpaceClassroomMemberViewSet.as_view({'get': 'list'}), name='classroom-members-list'),
    path('<str:classroom_uid>/members/join/', SpaceClassroomMemberViewSet.as_view({'post': 'join'}), name='classroom-members-join'),
    path('<str:classroom_uid>/members/leave/', SpaceClassroomMemberViewSet.as_view({'post': 'leave'}), name='classroom-members-leave'),
    path('<str:classroom_uid>/members/<str:member_id>/approve/', SpaceClassroomMemberViewSet.as_view({'post': 'approve'}), name='classroom-members-approve'),
    path('<str:classroom_uid>/members/<str:member_id>/reject/', SpaceClassroomMemberViewSet.as_view({'delete': 'reject'}), name='classroom-members-reject'),
    path('<str:classroom_uid>/members/<str:member_id>/kick/', SpaceClassroomMemberViewSet.as_view({'delete': 'kick'}), name='classroom-members-kick'),
    path('<str:classroom_uid>/members/<str:member_id>/submissions/', SpaceClassroomMemberViewSet.as_view({'get': 'student_submissions'}), name='classroom-members-submissions'),
    path('<str:classroom_uid>/members/<str:member_id>/stats/', SpaceClassroomMemberViewSet.as_view({'get': 'student_stats'}), name='classroom-members-stats'),
    path('<str:uid>/blacklist/', SpaceClassroomBlacklistView.as_view(), name='classroom-blacklist'),
    path('<str:uid>/blacklist/<str:consumer_uid>/', SpaceClassroomBlacklistDetailView.as_view(), name='classroom-blacklist-detail'),
]
