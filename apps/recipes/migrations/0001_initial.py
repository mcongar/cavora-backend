import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Ingredient",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("slug", models.SlugField(db_index=True, max_length=80, unique=True)),
                ("name_es", models.CharField(max_length=120)),
                ("name_en", models.CharField(blank=True, max_length=120)),
                (
                    "category",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("dairy", "Dairy"),
                            ("fruits", "Fruits"),
                            ("vegetables", "Vegetables"),
                            ("meat", "Meat"),
                            ("fish", "Fish"),
                            ("beverages", "Beverages"),
                            ("snacks", "Snacks"),
                            ("cereals", "Cereals"),
                            ("frozen", "Frozen"),
                            ("condiments", "Condiments"),
                            ("bakery", "Bakery"),
                            ("canned", "Canned"),
                            ("other", "Other"),
                        ],
                        help_text="Optional hint for admin and fallbacks.",
                        max_length=20,
                        null=True,
                    ),
                ),
            ],
            options={
                "db_table": "recipe_ingredients",
                "ordering": ["slug"],
            },
        ),
        migrations.CreateModel(
            name="Recipe",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title_es", models.CharField(max_length=200)),
                ("title_en", models.CharField(blank=True, max_length=200)),
                ("steps_es", models.TextField(help_text="Preparation steps (plain text or simple lines).")),
                ("steps_en", models.TextField(blank=True)),
                ("prep_minutes", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("is_published", models.BooleanField(db_index=True, default=False)),
            ],
            options={
                "db_table": "recipes",
                "ordering": ["title_es"],
            },
        ),
        migrations.CreateModel(
            name="RecipeIngredient",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("required", models.BooleanField(db_index=True, default=True)),
                ("quantity_note", models.CharField(blank=True, max_length=120)),
                (
                    "ingredient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="recipe_links",
                        to="recipes.ingredient",
                    ),
                ),
                (
                    "recipe",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="recipe_ingredients",
                        to="recipes.recipe",
                    ),
                ),
            ],
            options={
                "db_table": "recipe_recipe_ingredients",
                "unique_together": {("recipe", "ingredient")},
            },
        ),
        migrations.CreateModel(
            name="ProductCatalogIngredient",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "catalog_product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ingredient_mappings",
                        to="catalog.productcatalog",
                    ),
                ),
                (
                    "ingredient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="catalog_products",
                        to="recipes.ingredient",
                    ),
                ),
            ],
            options={
                "db_table": "recipe_product_catalog_ingredients",
                "unique_together": {("catalog_product", "ingredient")},
            },
        ),
        migrations.CreateModel(
            name="CategoryIngredientDefault",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("dairy", "Dairy"),
                            ("fruits", "Fruits"),
                            ("vegetables", "Vegetables"),
                            ("meat", "Meat"),
                            ("fish", "Fish"),
                            ("beverages", "Beverages"),
                            ("snacks", "Snacks"),
                            ("cereals", "Cereals"),
                            ("frozen", "Frozen"),
                            ("condiments", "Condiments"),
                            ("bakery", "Bakery"),
                            ("canned", "Canned"),
                            ("other", "Other"),
                        ],
                        db_index=True,
                        max_length=20,
                    ),
                ),
                (
                    "ingredient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="category_defaults",
                        to="recipes.ingredient",
                    ),
                ),
            ],
            options={
                "db_table": "recipe_category_ingredient_defaults",
                "unique_together": {("category", "ingredient")},
            },
        ),
    ]
