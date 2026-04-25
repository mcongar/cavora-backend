from django.urls import path
from .views import (
    UserProductListCreateView,
    UserProductDetailView,
    ConsumeProductView,
    WasteProductView,
    ScanSessionCreateView,
    BulkAddView,
    SessionRollbackView,
    DashboardStatsView,
    ShelfHintView,
    SplitProductView,
)

urlpatterns = [
    path("stats/dashboard/", DashboardStatsView.as_view()),
    path("shelf-hint/", ShelfHintView.as_view()),
    path("products/", UserProductListCreateView.as_view()),
    path("products/<uuid:pk>/", UserProductDetailView.as_view()),
    path("products/<uuid:pk>/consume/", ConsumeProductView.as_view()),
    path("products/<uuid:pk>/waste/", WasteProductView.as_view()),
    path("products/<uuid:pk>/split/", SplitProductView.as_view()),
    path("sessions/", ScanSessionCreateView.as_view()),
    path("sessions/<uuid:pk>/bulk-add/", BulkAddView.as_view()),
    path("sessions/<uuid:pk>/", SessionRollbackView.as_view()),
]
