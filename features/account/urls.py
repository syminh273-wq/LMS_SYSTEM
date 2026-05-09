from django.urls import include, path

urlpatterns = [
    path('', include('features.account.consumer.urls')),
    path('', include('features.account.space.urls')),
]
