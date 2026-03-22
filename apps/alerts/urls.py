from django.urls import path
from .views import AlertListView, DismissAlertView

urlpatterns = [
    path("", AlertListView.as_view()),
    path("<uuid:pk>/dismiss/", DismissAlertView.as_view()),
]
