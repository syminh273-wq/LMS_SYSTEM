from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from core.views.ws_test_view import test_chat_view

urlpatterns = [
    path('', RedirectView.as_view(url='api/v1/account/'), name='index'),
    path('admin/', admin.site.urls),
    path('api/v1/account/', include('features.account.urls')),
    path('api/v1/', include('core.urls')),
    path('test-chat/<str:room_name>/', test_chat_view, name='test_chat'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
