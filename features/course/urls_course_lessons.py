from django.urls import path
from features.course.viewsets import CourseLessonViewSet


_lesson = CourseLessonViewSet.as_view({
    'get': 'list',
    'post': 'create',
})

_lesson_detail = CourseLessonViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy',
})

_lesson_reorder = CourseLessonViewSet.as_view({
    'post': 'reorder',
})


urlpatterns = [
    path('<str:course_uid>/lessons/', _lesson, name='course-lessons-list'),
    path('<str:course_uid>/lessons/reorder/', _lesson_reorder, name='course-lessons-reorder'),
    path('<str:course_uid>/lessons/<str:uid>/', _lesson_detail, name='course-lessons-detail'),
]
