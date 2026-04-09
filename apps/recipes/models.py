from django.db import models

from apps.catalog.choices import Category
from apps.catalog.models import ProductCatalog
from common.models import BaseModel


class Ingredient(BaseModel):
    """Canonical ingredient for recipe matching and pantry resolution."""

    slug = models.SlugField(max_length=80, unique=True, db_index=True)
    name_es = models.CharField(max_length=120)
    name_en = models.CharField(max_length=120, blank=True)
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        null=True,
        blank=True,
        help_text="Optional hint for admin and fallbacks.",
    )

    class Meta:
        db_table = "recipe_ingredients"
        ordering = ["slug"]

    def __str__(self):
        return self.name_es or self.slug


class Recipe(BaseModel):
    title_es = models.CharField(max_length=200)
    title_en = models.CharField(max_length=200, blank=True)
    steps_es = models.TextField(help_text="Preparation steps (plain text or simple lines).")
    steps_en = models.TextField(blank=True)
    prep_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    is_published = models.BooleanField(default=False, db_index=True)
    ai_generated = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Created by the AI recipe generator (batch or on-demand).",
    )

    class Meta:
        db_table = "recipes"
        ordering = ["title_es"]

    def __str__(self):
        return self.title_es


class RecipeIngredient(BaseModel):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="recipe_ingredients")
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name="recipe_links")
    required = models.BooleanField(default=True, db_index=True)
    quantity_note = models.CharField(max_length=120, blank=True)

    class Meta:
        db_table = "recipe_recipe_ingredients"
        unique_together = [("recipe", "ingredient")]

    def __str__(self):
        return f"{self.recipe_id} · {self.ingredient_id}"


class ProductCatalogIngredient(BaseModel):
    """Maps a catalog product to one or more canonical ingredients."""

    catalog_product = models.ForeignKey(
        ProductCatalog, on_delete=models.CASCADE, related_name="ingredient_mappings"
    )
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name="catalog_products")

    class Meta:
        db_table = "recipe_product_catalog_ingredients"
        unique_together = [("catalog_product", "ingredient")]

    def __str__(self):
        return f"{self.catalog_product_id} → {self.ingredient.slug}"


class CategoryIngredientDefault(BaseModel):
    """Fallback: manual pantry lines (no catalog) get ingredients by category."""

    category = models.CharField(max_length=20, choices=Category.choices, db_index=True)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name="category_defaults")

    class Meta:
        db_table = "recipe_category_ingredient_defaults"
        unique_together = [("category", "ingredient")]

    def __str__(self):
        return f"{self.category} → {self.ingredient.slug}"
