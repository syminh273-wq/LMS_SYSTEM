from django.urls import path, include
from rest_framework.routers import DefaultRouter
from features.payment.viewsets.payment_viewset import PaymentViewSet
from features.payment.viewsets.space_payment_viewset import SpacePaymentViewSet
from features.payment.viewsets.ipn_viewset import MoMoIPNView

router = DefaultRouter()
router.register(r'', PaymentViewSet, basename='payment')

space_router = DefaultRouter()
space_router.register(r'', SpacePaymentViewSet, basename='space-payment')

urlpatterns = [
    path('ipn/', MoMoIPNView.as_view(), name='momo-ipn'),
    path('', include(router.urls)),
]
