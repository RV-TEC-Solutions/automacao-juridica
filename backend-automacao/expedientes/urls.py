from rest_framework.routers import DefaultRouter

from django.urls import path

from .views import ExpedienteViewSet, clientes, dashboard, history, mark_all_read, mark_read, statistics
from .reports import export_expedientes

router = DefaultRouter()

router.register(
    "expedientes",
    ExpedienteViewSet,
    basename="expediente",
)

urlpatterns = [
    path("expedientes/clientes/", clientes, name="expedientes-clientes"),
    path("dashboard/", dashboard, name="dashboard"),
    path("statistics/", statistics, name="statistics"),
    path("history/", history, name="history"),
    path("expedientes/read-all/", mark_all_read, name="expedientes-read-all"),
    path("expedientes/<int:pk>/read/", mark_read, name="expediente-read"),
    path("expedientes/export.pdf/", export_expedientes, name="expedientes-export"),
] + router.urls
