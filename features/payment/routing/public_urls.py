from django.urls import path
from features.payment.views.ipn_views import MoMoIPNView

urlpatterns = [
    path('ipn/', MoMoIPNView.as_view(), name='momo-ipn'),
]
