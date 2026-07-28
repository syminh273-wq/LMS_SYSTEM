from django.urls import path
from features.portfolio.views import PublicPortfolioView

urlpatterns = [
    path('<str:owner_type>/<str:owner_id>/', PublicPortfolioView.as_view(), name='portfolio-public'),
]
