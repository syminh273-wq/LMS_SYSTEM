from django.urls import path, include
from rest_framework.routers import DefaultRouter
from features.payment.viewsets.space_payment_viewset import SpacePaymentViewSet

router = DefaultRouter()
router.register(r'', SpacePaymentViewSet, basename='space-payment')

urlpatterns = [
    path('', include(router.urls)),
]
