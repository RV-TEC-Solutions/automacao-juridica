from rest_framework.routers import DefaultRouter

from django.urls import path

from .views import ExpedienteViewSet, dashboard, mark_read, statistics

router = DefaultRouter()

router.register(
    "expedientes",
    ExpedienteViewSet,
    basename="expediente",
)

urlpatterns = [
    path("dashboard/", dashboard, name="dashboard"),
    path("statistics/", statistics, name="statistics"),
    path("expedientes/<int:pk>/read/", mark_read, name="expediente-read"),
] + router.urls
