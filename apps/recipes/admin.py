from django.contrib import admin

from .models import (
    CategoryIngredientDefault,
    Ingredient,
    ProductCatalogIngredient,
    Recipe,
    RecipeIngredient,
)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    autocomplete_fields = ("ingredient",)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("slug", "name_es", "name_en", "category")
    search_fields = ("slug", "name_es", "name_en")
    list_filter = ("category",)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("title_es", "is_published", "ai_generated", "prep_minutes")
    list_filter = ("is_published", "ai_generated")
    search_fields = ("title_es", "title_en")
    inlines = (RecipeIngredientInline,)


@admin.register(ProductCatalogIngredient)
class ProductCatalogIngredientAdmin(admin.ModelAdmin):
    list_display = ("catalog_product", "ingredient")
    autocomplete_fields = ("catalog_product", "ingredient")


@admin.register(CategoryIngredientDefault)
class CategoryIngredientDefaultAdmin(admin.ModelAdmin):
    list_display = ("category", "ingredient")
    list_filter = ("category",)
    autocomplete_fields = ("ingredient",)
