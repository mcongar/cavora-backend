from django.urls import path

from .views import BarcodeView, ProductSearchView

urlpatterns = [
    path("barcode/<str:code>/", BarcodeView.as_view()),
    path("search/", ProductSearchView.as_view()),
]
