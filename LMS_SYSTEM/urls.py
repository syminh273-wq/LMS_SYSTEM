from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from core.views.ws_test_view import test_chat_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/consumer/account/', include('features.account.consumer.urls')),
    path('api/v1/consumer/course/', include('features.course.consumer_urls')),
    path('api/v1/space/account/', include('features.account.space.urls')),
    path('api/v1/space/course/', include('features.course.urls')),
    path('api/v1/sharing/', include('features.sharing.urls')),
    path('api/v1/resource/', include('features.resource.urls')),
    path('api/v1/chat/', include('features.chat.urls')),
    path('api/v1/public/', include('core.urls')),
    path('test-chat/<str:room_name>/', test_chat_view, name='test_chat'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
