from django.urls import path, include
from rest_framework.routers import DefaultRouter
from features.course.classroom.viewsets import ClassroomViewSet, ClassroomMemberViewSet, ClassroomAIViewSet
from features.course.classroom.views.classroom_blacklist_views import (
    ClassroomBlacklistView,
    ClassroomBlacklistDetailView,
)

router = DefaultRouter()
router.register(r'', ClassroomViewSet, basename='classroom')

urlpatterns = [
    path('', include(router.urls)),
    # POST upload doc / GET list docs /classrooms/<uid>/docs/
    path('<str:uid>/docs/',
         ClassroomViewSet.as_view({'post': 'docs_upload', 'get': 'docs_list'}),
         name='classroom-docs'),
    # DELETE /classrooms/<uid>/docs/<resource_uid>/
    path('<str:uid>/docs/<str:resource_uid>/',
         ClassroomViewSet.as_view({'delete': 'docs_delete'}),
         name='classroom-docs-delete'),
    # AI Q&A bot — served by ClassroomAIViewSet
    path('<str:uid>/ask/',
         ClassroomAIViewSet.as_view({'post': 'ask'}),
         name='classroom-ask'),
    path('<str:uid>/ask-stream/',
         ClassroomAIViewSet.as_view({'post': 'ask_stream'}),
         name='classroom-ask-stream'),
    path('<str:uid>/active-session/',
         ClassroomAIViewSet.as_view({'get': 'active_session'}),
         name='classroom-active-session'),
    path('<str:uid>/ai-session/',
         ClassroomAIViewSet.as_view({'post': 'ai_session'}),
         name='classroom-ai-session'),
    path('<str:uid>/ai-sessions/',
         ClassroomAIViewSet.as_view({'get': 'ai_sessions'}),
         name='classroom-ai-sessions'),
    path('<str:uid>/ai-session/history/',
         ClassroomAIViewSet.as_view({'get': 'ai_session_history'}),
         name='classroom-ai-session-history'),
    path('<str:classroom_uid>/members/', ClassroomMemberViewSet.as_view({'get': 'list'}), name='classroom-members-list'),
    path('<str:classroom_uid>/members/join/', ClassroomMemberViewSet.as_view({'post': 'join'}), name='classroom-members-join'),
    path('<str:classroom_uid>/members/leave/', ClassroomMemberViewSet.as_view({'post': 'leave'}), name='classroom-members-leave'),
    path('<str:classroom_uid>/members/<str:member_id>/approve/', ClassroomMemberViewSet.as_view({'post': 'approve'}), name='classroom-members-approve'),
    path('<str:classroom_uid>/members/<str:member_id>/reject/', ClassroomMemberViewSet.as_view({'delete': 'reject'}), name='classroom-members-reject'),
    path('<str:classroom_uid>/members/<str:member_id>/kick/', ClassroomMemberViewSet.as_view({'delete': 'kick'}), name='classroom-members-kick'),
    path('<str:classroom_uid>/members/<str:member_id>/submissions/', ClassroomMemberViewSet.as_view({'get': 'student_submissions'}), name='classroom-members-submissions'),
    path('<str:uid>/blacklist/', ClassroomBlacklistView.as_view(), name='classroom-blacklist'),
    path('<str:uid>/blacklist/<str:consumer_uid>/', ClassroomBlacklistDetailView.as_view(), name='classroom-blacklist-detail'),
]
