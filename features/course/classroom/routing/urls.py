from django.urls import path, include
from rest_framework.routers import DefaultRouter
from features.course.classroom.viewsets import ClassroomViewSet, ClassroomMemberViewSet
from features.course.classroom.views.classroom_blacklist_views import (
    ClassroomBlacklistView,
    ClassroomBlacklistDetailView,
)

router = DefaultRouter()
router.register(r'', ClassroomViewSet, basename='classroom')

urlpatterns = [
    path('', include(router.urls)),
    # DELETE /classrooms/<uid>/docs/<resource_uid>/
    path('<str:uid>/docs/<str:resource_uid>/',
         ClassroomViewSet.as_view({'delete': 'docs_delete'}),
         name='classroom-docs-delete'),
    # POST /classrooms/<uid>/ask-stream/  — SSE streaming AI bot
    path('<str:uid>/ask-stream/',
         ClassroomViewSet.as_view({'post': 'ask_stream'}),
         name='classroom-ask-stream'),
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
