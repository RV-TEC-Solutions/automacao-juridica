from django.urls import path

from .views import (
    change_password, csrf, login_view, logout_view, me, runs,
    settings_view, source_detail, sources,
)

urlpatterns = [
    path("auth/csrf/", csrf), path("auth/login/", login_view),
    path("auth/logout/", logout_view), path("auth/me/", me),
    path("auth/password/", change_password), path("settings/", settings_view),
    path("sources/", sources), path("sources/<slug:code>/", source_detail),
    path("automation/runs/", runs),
]
