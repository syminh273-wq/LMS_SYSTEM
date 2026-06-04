from django.urls import include, path

urlpatterns = [
    path('', include('features.account.consumer.urls')),
    path('', include('features.account.space.urls')),
    path('voice-settings/', include('features.account.voice_setting.urls')),
]
