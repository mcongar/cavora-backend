from django.urls import path
from .views import (
    UserProductListCreateView,
    UserProductDetailView,
    ConsumeProductView,
    ScanSessionCreateView,
    BulkAddView,
    SessionRollbackView,
)

urlpatterns = [
    path("products/", UserProductListCreateView.as_view()),
    path("products/<uuid:pk>/", UserProductDetailView.as_view()),
    path("products/<uuid:pk>/consume/", ConsumeProductView.as_view()),
    path("sessions/", ScanSessionCreateView.as_view()),
    path("sessions/<uuid:pk>/bulk-add/", BulkAddView.as_view()),
    path("sessions/<uuid:pk>/", SessionRollbackView.as_view()),
]
