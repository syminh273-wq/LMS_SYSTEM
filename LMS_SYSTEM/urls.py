from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from core.views.ws_test_view import test_chat_view
from core.views.search_api import SpaceSearchAPIView, SearchHealthAPIView
from features.account.space.views.public_teacher_views import PublicTeacherView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/consumer/account/', include('features.account.consumer.routing.public_urls')),
    path('api/v1/consumer/account/', include('features.account.consumer.routing.urls')),
    path('api/v1/consumer/course/', include('features.course.routing.consumer_urls')),
    path('api/v1/space/account/', include('features.account.space.routing.public_urls')),
    path('api/v1/space/account/', include('features.account.space.routing.urls')),
    path('api/v1/account/user-settings/', include('features.account.user_setting.routing.urls')),
    path('api/v1/account/addresses/', include('features.account.routing.urls')),
    path('api/v1/space/course/', include('features.course.routing.urls')),
    path('api/v1/resource/', include('features.resource.routing.urls')),
    path('api/v1/chat/', include('features.chat.routing.urls')),
    path('api/v1/space/quiz/', include('features.quiz.routing.urls')),
    path('api/v1/consumer/quiz/', include('features.quiz.routing.consumer_urls')),
    path('api/v1/space/', include('features.quiz_collection.routing.urls')),
    path('api/v1/consumer/quiz-collection/', include('features.quiz_collection.routing.consumer_urls')),
    path('api/v1/notifications/', include('features.notification.routing.urls')),
    path('api/v1/space/calendar/', include('features.calendar.routing.urls')),
    path('api/v1/consumer/calendar/', include('features.calendar.routing.consumer_urls')),
    path('api/v1/consumer/payment/', include('features.payment.routing.public_urls')),
    path('api/v1/consumer/payment/', include('features.payment.routing.urls')),
    path('api/v1/space/payment/', include('features.payment.routing.space_urls')),
    path('api/v1/space/dashboard/', include('features.dashboard.routing.urls')),
    path('api/v1/consumer/face/', include('features.face.routing.urls')),
    path('api/v1/space/face/', include('features.face.routing.space_urls')),
    path('api/v1/consumer/social/', include('features.social.routing.urls')),
    path('api/v1/space/social/',    include('features.social.routing.urls')),
    path('api/v1/portfolio/', include('features.portfolio.routing.urls')),
    path('api/v1/portfolio/', include('features.portfolio.routing.public_urls')),
    path('api/v1/consumer/ranking/', include('features.ranking.routing.consumer_urls')),
    path('api/v1/space/ranking/', include('features.ranking.routing.space_urls')),
    path('api/v1/public/', include('core.urls')),
    # Public course preview (no auth) — must be inside /api/v1/public/
    # PublicCourseViewSet removed in Phase 3 (course_courses dropped).
    # TODO: re-implement as a no-op stub or via classroom preview.
    # path('api/v1/public/course/preview/<str:code>/', PublicCourseViewSet.as_view(), name='public-course-preview'),
    path('api/v1/public/teachers/<uuid:uid>/', PublicTeacherView.as_view(), name='public-teacher'),
    path('api/v1/space/search/', SpaceSearchAPIView.as_view(), name='space-search'),
    path('api/v1/space/search/health/', SearchHealthAPIView.as_view(), name='search-health'),
    path('test-chat/<str:room_name>/', test_chat_view, name='test-chat'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
