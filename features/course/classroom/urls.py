from django.urls import path, include
from rest_framework.routers import DefaultRouter
from features.course.classroom.viewsets import ClassroomViewSet, ClassroomMemberViewSet

router = DefaultRouter()
router.register(r'', ClassroomViewSet, basename='classroom')

urlpatterns = [
    path('', include(router.urls)),
    # Nested member routes: /classrooms/<classroom_uid>/members/
    path(
        '<str:classroom_uid>/members/',
        ClassroomMemberViewSet.as_view({'get': 'list'}),
        name='classroom-members-list',
    ),
    path(
        '<str:classroom_uid>/members/join/',
        ClassroomMemberViewSet.as_view({'post': 'join'}),
        name='classroom-members-join',
    ),
    path(
        '<str:classroom_uid>/members/leave/',
        ClassroomMemberViewSet.as_view({'post': 'leave'}),
        name='classroom-members-leave',
    ),
]
