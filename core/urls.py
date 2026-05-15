from django.urls import path
from core.views.storage_views import upload_file, get_file, list_files, delete_file

app_name = 'core'

urlpatterns = [
    path('storage/upload/', upload_file, name='upload_file'),
    path('storage/files/', list_files, name='list_files'),
    path('storage/files/<path:object_key>/', get_file, name='get_file'),
    path('storage/files/<path:object_key>/delete/', delete_file, name='delete_file'),
]
