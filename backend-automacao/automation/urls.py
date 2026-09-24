from django.urls import path

from .views import (
    cancel_run, change_password, csrf, login_view, logout_view, me, runs,
    settings_view, source_detail, sources, notices, notice_detail, mark_notice_read,
)

urlpatterns = [
    path("auth/csrf/", csrf), path("auth/login/", login_view),
    path("auth/logout/", logout_view), path("auth/me/", me),
    path("auth/password/", change_password), path("settings/", settings_view),
    path("sources/", sources), path("sources/<slug:code>/", source_detail),
    path("automation/runs/", runs),
    path("automation/runs/<int:pk>/cancel/", cancel_run),
    path("notices/", notices),
    path("notices/<int:pk>/", notice_detail),
    path("notices/<int:pk>/read/", mark_notice_read),
]
