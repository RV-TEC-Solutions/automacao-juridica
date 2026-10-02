from rest_framework.routers import DefaultRouter

from django.urls import path

from .views import ExpedienteViewSet, dashboard, history, mark_read, statistics
from .reports import export_expedientes

router = DefaultRouter()

router.register(
    "expedientes",
    ExpedienteViewSet,
    basename="expediente",
)

urlpatterns = [
    path("dashboard/", dashboard, name="dashboard"),
    path("statistics/", statistics, name="statistics"),
    path("history/", history, name="history"),
    path("expedientes/<int:pk>/read/", mark_read, name="expediente-read"),
    path("expedientes/export.pdf/", export_expedientes, name="expedientes-export"),
] + router.urls
