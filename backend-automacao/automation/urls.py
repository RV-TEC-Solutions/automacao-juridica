from django.urls import path

from .views import (
    cancel_run, change_password, collection_history, csrf, discard_today_collection,
    login_view, logout_view, me, runs,
    settings_view, source_detail, sources, notices, notice_detail, mark_notice_read, token_status,
    djen_communications, djen_communication_detail, djen_history, mark_djen_read,
)
from .reports import export_publications

urlpatterns = [
    path("auth/csrf/", csrf), path("auth/login/", login_view),
    path("auth/logout/", logout_view), path("auth/me/", me),
    path("auth/password/", change_password), path("settings/", settings_view),
    path("sources/", sources), path("sources/<slug:code>/", source_detail),
    path("automation/runs/", runs),
    path("automation/token-status/", token_status),
    path("automation/runs/<int:pk>/cancel/", cancel_run),
    path("automation/collections/today/discard/", discard_today_collection),
    path("automation/history/", collection_history),
    path("notices/", notices),
    path("notices/<int:pk>/", notice_detail),
    path("notices/<int:pk>/read/", mark_notice_read),
    path("djen/communications/", djen_communications),
    path("djen/communications/export.pdf/", export_publications),
    path("djen/history/", djen_history),
    path("djen/communications/<int:pk>/", djen_communication_detail),
    path("djen/communications/<int:pk>/read/", mark_djen_read),
]
