from django.urls import path

from .views import RecipeDetailView, RecipeGenerateForProductView, RecipeListView

urlpatterns = [
    path("", RecipeListView.as_view()),
    path("generate-for-product/", RecipeGenerateForProductView.as_view()),
    path("<uuid:pk>/", RecipeDetailView.as_view()),
]
