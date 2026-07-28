from django.urls import path
from features.portfolio.views import (
    MyPortfolioView,
    PortfolioEntryCreateView,
    PortfolioEntryDetailView,
    PortfolioReorderView,
    PortfolioUploadView,
)

urlpatterns = [
    path('me/', MyPortfolioView.as_view(), name='portfolio-me'),
    path('me/upload/', PortfolioUploadView.as_view(), name='portfolio-me-upload'),
    path('me/reorder/', PortfolioReorderView.as_view(), name='portfolio-me-reorder'),
    path('me/entries/', PortfolioEntryCreateView.as_view(), name='portfolio-me-entry-create'),
    path('me/entries/<str:uid>/', PortfolioEntryDetailView.as_view(), name='portfolio-me-entry'),
]
