from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from core.views.ws_test_view import test_chat_view
from core.views.search_api import SpaceSearchAPIView, SearchHealthAPIView
from features.course.viewsets import PublicCourseViewSet
from features.account.space.viewsets.public_teacher_view import PublicTeacherView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/consumer/account/', include('features.account.consumer.urls')),
    path('api/v1/consumer/course/', include('features.course.consumer_urls')),
    path('api/v1/space/account/', include('features.account.space.urls')),
    path('api/v1/account/user-settings/', include('features.account.user_setting.urls')),
    path('api/v1/space/course/', include('features.course.urls')),
    path('api/v1/sharing/', include('features.sharing.urls')),
    path('api/v1/resource/', include('features.resource.urls')),
    path('api/v1/chat/', include('features.chat.urls')),
    path('api/v1/space/quiz/', include('features.quiz.urls')),
    path('api/v1/consumer/quiz/', include('features.quiz.consumer_urls')),
    path('api/v1/space/quiz-collection/', include('features.quiz_collection.urls')),
    path('api/v1/consumer/quiz-collection/', include('features.quiz_collection.consumer_urls')),
    path('api/v1/space/certificate/', include('features.quiz_collection.certificate_urls')),
    path('api/v1/notifications/', include('features.notification.urls')),
    path('api/v1/space/calendar/', include('features.calendar.urls')),
    path('api/v1/consumer/calendar/', include('features.calendar.consumer_urls')),
    path('api/v1/consumer/payment/', include('features.payment.urls')),
    path('api/v1/consumer/face/', include('features.face.urls')),
    path('api/v1/space/face/', include('features.face.space_urls')),
    path('api/v1/consumer/social/', include('features.social.urls')),
    path('api/v1/space/social/',    include('features.social.urls')),
    path('api/v1/portfolio/', include('features.portfolio.urls')),
    path('api/v1/public/', include('core.urls')),
    # Public course preview (no auth) — must be inside /api/v1/public/
    path('api/v1/public/course/preview/<str:code>/', PublicCourseViewSet.as_view(), name='public-course-preview'),
    path('api/v1/public/teachers/<uuid:uid>/', PublicTeacherView.as_view(), name='public-teacher'),
    path('api/v1/space/search/', SpaceSearchAPIView.as_view(), name='space-search'),
    path('api/v1/space/search/health/', SearchHealthAPIView.as_view(), name='search-health'),
    path('test-chat/<str:room_name>/', test_chat_view, name='test-chat'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
