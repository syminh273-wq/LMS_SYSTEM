from django.urls import include, path

urlpatterns = [
    path('', include('features.account.consumer.urls')),
    path('', include('features.account.space.urls')),
    path('user-settings/', include('features.account.user_setting.urls')),
]
