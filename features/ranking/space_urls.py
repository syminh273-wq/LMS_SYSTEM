from django.urls import path

from features.ranking.viewsets.space_ranking_viewset import (
    SpaceRankingStudentViewSet,
    SpaceRankingAchievementsViewSet,
    SpaceRankingClassroomViewSet,
    SpaceRankingStudentClassroomViewSet,
)


urlpatterns = [
    path('students/<str:student_uid>/',
         SpaceRankingStudentViewSet.as_view(),
         name='space-ranking-student'),
    path('students/<str:student_uid>/achievements/',
         SpaceRankingAchievementsViewSet.as_view(),
         name='space-ranking-student-achievements'),
    path('students/<str:student_uid>/classroom/<str:classroom_uid>/',
         SpaceRankingStudentClassroomViewSet.as_view(),
         name='space-ranking-student-classroom'),
    path('classrooms/<str:classroom_uid>/leaderboard/',
         SpaceRankingClassroomViewSet.as_view(),
         name='space-ranking-classroom-leaderboard'),
]
