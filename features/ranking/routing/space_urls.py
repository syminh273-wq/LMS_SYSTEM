from django.urls import path

from features.ranking.views.space_ranking_views import (
    SpaceRankingStudentView,
    SpaceRankingAchievementsView,
    SpaceRankingClassroomView,
    SpaceRankingStudentClassroomView,
)


urlpatterns = [
    path('students/<str:student_uid>/',
         SpaceRankingStudentView.as_view(),
         name='space-ranking-student'),
    path('students/<str:student_uid>/achievements/',
         SpaceRankingAchievementsView.as_view(),
         name='space-ranking-student-achievements'),
    path('students/<str:student_uid>/classroom/<str:classroom_uid>/',
         SpaceRankingStudentClassroomView.as_view(),
         name='space-ranking-student-classroom'),
    path('classrooms/<str:classroom_uid>/leaderboard/',
         SpaceRankingClassroomView.as_view(),
         name='space-ranking-classroom-leaderboard'),
]
