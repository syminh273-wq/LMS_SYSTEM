from django.urls import path, include
from rest_framework.routers import DefaultRouter
from features.course.classroom.viewsets import ClassroomViewSet, ClassroomMemberViewSet

router = DefaultRouter()
router.register(r'', ClassroomViewSet, basename='classroom')

_member = ClassroomMemberViewSet

urlpatterns = [
    path('', include(router.urls)),
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
]
