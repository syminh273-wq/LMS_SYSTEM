from rest_framework.viewsets import ModelViewSet
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend


class BaseModelViewSet(ModelViewSet):
    filter_backends  = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    lookup_field     = 'uid'
