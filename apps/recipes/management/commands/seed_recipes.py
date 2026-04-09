from django.core.management.base import BaseCommand

from apps.catalog.choices import Category
from apps.catalog.models import ProductCatalog
from apps.recipes.models import (
    CategoryIngredientDefault,
    Ingredient,
    ProductCatalogIngredient,
    Recipe,
    RecipeIngredient,
)


def _ensure_recipe(title_es: str, **fields) -> Recipe:
    r = Recipe.objects.filter(title_es=title_es).first()
    if r:
        for k, v in fields.items():
            setattr(r, k, v)
        r.save()
        return r
    return Recipe.objects.create(title_es=title_es, **fields)


class Command(BaseCommand):
    help = "Seed canonical ingredients, category defaults, and a few published recipes (idempotent by title_es)."

    def handle(self, *args, **options):
        defs = [
            ("milk", "Leche", "Milk", Category.DAIRY),
            ("eggs", "Huevos", "Eggs", Category.DAIRY),
            ("pasta", "Pasta", "Pasta", Category.CEREALS),
            ("tomato", "Tomate", "Tomato", Category.VEGETABLES),
        ]
        ings = {}
        for slug, es, en, cat in defs:
            ing, _ = Ingredient.objects.update_or_create(
                slug=slug,
                defaults={"name_es": es, "name_en": en, "category": cat},
            )
            ings[slug] = ing
            self.stdout.write(f"Ingredient: {slug}")

        for cat in (Category.DAIRY, Category.VEGETABLES, Category.CEREALS):
            for slug in {
                Category.DAIRY: ("milk", "eggs"),
                Category.VEGETABLES: ("tomato",),
                Category.CEREALS: ("pasta",),
            }.get(cat, ()):
                CategoryIngredientDefault.objects.get_or_create(
                    category=cat, ingredient=ings[slug]
                )

        r1 = _ensure_recipe(
            "Tortilla rápida",
            title_en="Quick omelette",
            steps_es="1. Batir los huevos.\n2. Calentar la sartén con un poco de leche si queda.\n3. Cuajar y servir.",
            steps_en="1. Beat eggs.\n2. Warm pan.\n3. Cook and serve.",
            prep_minutes=15,
            is_published=True,
        )
        RecipeIngredient.objects.filter(recipe=r1).delete()
        RecipeIngredient.objects.create(recipe=r1, ingredient=ings["eggs"], required=True)
        RecipeIngredient.objects.create(
            recipe=r1, ingredient=ings["milk"], required=False, quantity_note="opcional"
        )

        r2 = _ensure_recipe(
            "Pasta con tomate",
            title_en="Pasta with tomato",
            steps_es="1. Cocer la pasta.\n2. Saltear el tomate.\n3. Mezclar.",
            steps_en="1. Boil pasta.\n2. Sauté tomato.\n3. Combine.",
            prep_minutes=25,
            is_published=True,
        )
        RecipeIngredient.objects.filter(recipe=r2).delete()
        RecipeIngredient.objects.create(recipe=r2, ingredient=ings["pasta"], required=True)
        RecipeIngredient.objects.create(recipe=r2, ingredient=ings["tomato"], required=True)

        self.stdout.write(self.style.SUCCESS("Recipes seeded."))

        for barcode, slug in [("milk-bar", "milk"), ("eggs-bar", "eggs")]:
            cat = ProductCatalog.objects.filter(barcode=barcode).first()
            if cat:
                ProductCatalogIngredient.objects.get_or_create(
                    catalog_product=cat, ingredient=ings[slug]
                )
                self.stdout.write(f"Linked catalog {barcode} -> {slug}")
