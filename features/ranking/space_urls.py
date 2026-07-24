from django.urls import path

from features.ranking.viewsets.space_ranking_viewset import (
    SpaceRankingStudentViewSet,
    SpaceRankingAchievementsViewSet,
    SpaceRankingClassroomViewSet,
)


urlpatterns = [
    path('students/<str:student_uid>/',
         SpaceRankingStudentViewSet.as_view(),
         name='space-ranking-student'),
    path('students/<str:student_uid>/achievements/',
         SpaceRankingAchievementsViewSet.as_view(),
         name='space-ranking-student-achievements'),
    path('classrooms/<str:classroom_uid>/xp/',
         SpaceRankingClassroomViewSet.as_view(),
         name='space-ranking-classroom-xp'),
]
