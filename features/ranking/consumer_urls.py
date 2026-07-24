from django.urls import path

from features.ranking.viewsets.consumer_ranking_viewset import (
    MeView,
    MeTransactionsView,
    MeAchievementsView,
    MeLeaderboardView,
    LeaderboardView,
    LevelsView,
    AchievementsCatalogView,
    ClassroomLeaderboardView,
    MeClassroomStatsView,
)


urlpatterns = [
    path('me/', MeView.as_view(), name='ranking-me'),
    path('me/transactions/', MeTransactionsView.as_view(), name='ranking-me-transactions'),
    path('me/achievements/', MeAchievementsView.as_view(), name='ranking-me-achievements'),
    path('me/leaderboard/', MeLeaderboardView.as_view(), name='ranking-me-leaderboard'),
    path('me/classroom/<str:classroom_uid>/', MeClassroomStatsView.as_view(), name='ranking-me-classroom'),
    path('leaderboard/', LeaderboardView.as_view(), name='ranking-leaderboard'),
    path('classrooms/<str:classroom_uid>/leaderboard/', ClassroomLeaderboardView.as_view(), name='ranking-classroom-leaderboard'),
    path('levels/', LevelsView.as_view(), name='ranking-levels'),
    path('achievements/catalog/', AchievementsCatalogView.as_view(), name='ranking-achievements-catalog'),
]
