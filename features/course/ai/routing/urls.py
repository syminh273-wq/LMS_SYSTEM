from django.urls import path

from features.course.ai.viewsets.ai_viewset import CourseAIViewSet

ask_view         = CourseAIViewSet.as_view({"post":   "ask"})
ingest_view      = CourseAIViewSet.as_view({"post":   "ingest"})
index_view       = CourseAIViewSet.as_view({"delete": "delete_index"})

urlpatterns = [
    path("ask/",    ask_view,    name="course-ai-ask"),
    path("ingest/", ingest_view, name="course-ai-ingest"),
    path("index/",  index_view,  name="course-ai-index"),
]
