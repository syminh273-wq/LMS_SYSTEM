"""
URLs for the address endpoint, mounted at /api/v1/account/addresses/.
This is a top-level route so it can be used by both Consumer and Space
tokens without duplicating the address viewset under each app prefix.
"""
from django.urls import path
from features.account.consumer.viewsets.address_viewset import MyAddressView


urlpatterns = [
    path('me/', MyAddressView.as_view(), name='account-address-me'),
]
