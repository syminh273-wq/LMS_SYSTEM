from django.urls import path
from features.account.consumer.views.address_views import MyAddressView


urlpatterns = [
    path('me/', MyAddressView.as_view(), name='account-address-me'),
]
