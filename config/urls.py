from django.urls import path, include

urlpatterns = [
    path("api/v1/auth/", include("apps.auth.urls")),
    path("api/v1/chat/", include("apps.chat.urls")),
    path("api/v1/personas/", include("apps.personas.urls")),
    path("api/v1/notes/", include("apps.notes.urls")),
    path("api/v1/bookmarks/", include("apps.bookmarks.urls")),
    path("api/v1/rag/", include("apps.rag.urls")),
    path("api/v1/costs/", include("apps.costs.urls")),
    path("api/v1/agent/", include("apps.agent.urls")),
    path("api/v1/webhooks/", include("apps.webhooks.urls")),
]

# Admin URL — only registered when django.contrib.admin is installed
try:
    from django.contrib import admin
    urlpatterns.insert(0, path("admin/", admin.site.urls))
except Exception:
    pass
