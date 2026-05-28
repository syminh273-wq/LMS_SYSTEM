from django.urls import path, include
from rest_framework.routers import DefaultRouter
from features.payment.viewsets.payment_viewset import PaymentViewSet
from features.payment.viewsets.ipn_viewset import MoMoIPNView

router = DefaultRouter()
router.register(r'', PaymentViewSet, basename='payment')

urlpatterns = [
    path('ipn/', MoMoIPNView.as_view(), name='momo-ipn'),
    path('', include(router.urls)),
]
