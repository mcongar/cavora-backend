from datetime import date, timedelta
from unittest.mock import patch

from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.choices import Category
from apps.catalog.models import ProductCatalog
from apps.pantry.choices import AddMethod, ProductStatus
from apps.pantry.models import UserProduct
from apps.recipes.models import (
    CategoryIngredientDefault,
    Ingredient,
    ProductCatalogIngredient,
    Recipe,
    RecipeIngredient,
)
from apps.recipes.services.ai_recipe_generator import GeneratedRecipePayload, IngredientLine
from apps.recipes.services.pantry_recipe_ranking import (
    build_pantry_urgency_map,
    rank_recipes_for_user,
    score_recipe,
)
from apps.users.models import User


class PantryRecipeRankingTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="recipeuser",
            email="recipes@test.com",
            password="test-pass-123",
        )
        self.milk = Ingredient.objects.create(slug="milk", name_es="Leche", name_en="Milk", category=Category.DAIRY)
        self.eggs = Ingredient.objects.create(slug="eggs", name_es="Huevos", name_en="Eggs", category=Category.DAIRY)

        self.r_milk_only = Recipe.objects.create(
            title_es="Leche sola",
            steps_es="Beber.",
            is_published=True,
        )
        RecipeIngredient.objects.create(recipe=self.r_milk_only, ingredient=self.milk, required=True)

        self.r_eggs_only = Recipe.objects.create(
            title_es="Huevos",
            steps_es="Cocinar.",
            is_published=True,
        )
        RecipeIngredient.objects.create(recipe=self.r_eggs_only, ingredient=self.eggs, required=True)

        self.r_both = Recipe.objects.create(
            title_es="Tortilla",
            steps_es="Mezclar.",
            is_published=True,
        )
        RecipeIngredient.objects.create(recipe=self.r_both, ingredient=self.milk, required=True)
        RecipeIngredient.objects.create(recipe=self.r_both, ingredient=self.eggs, required=True)

        self.catalog_milk = ProductCatalog.objects.create(barcode="milk-bar", category=Category.DAIRY)
        ProductCatalogIngredient.objects.create(catalog_product=self.catalog_milk, ingredient=self.milk)

        self.catalog_eggs = ProductCatalog.objects.create(barcode="eggs-bar", category=Category.DAIRY)
        ProductCatalogIngredient.objects.create(catalog_product=self.catalog_eggs, ingredient=self.eggs)

    def test_urgency_ordering_milk_expires_first(self):
        UserProduct.objects.create(
            user=self.user,
            catalog_product=self.catalog_milk,
            add_method=AddMethod.BARCODE,
            status=ProductStatus.ACTIVE,
            quantity=1,
            expiry_date=date.today() + timedelta(days=1),
        )
        UserProduct.objects.create(
            user=self.user,
            catalog_product=self.catalog_eggs,
            add_method=AddMethod.BARCODE,
            status=ProductStatus.ACTIVE,
            quantity=1,
            expiry_date=date.today() + timedelta(days=10),
        )

        qs = Recipe.objects.filter(is_published=True)
        ranked, _ = rank_recipes_for_user(self.user, qs)
        ids = [r.id for r, _ in ranked]
        # Milk expires in 1 day, eggs in 10: tortilla and milk-only tie on urgency; eggs-only last.
        self.assertEqual(set(ids[:2]), {self.r_both.id, self.r_milk_only.id})
        self.assertEqual(ids[2], self.r_eggs_only.id)

    def test_score_missing_ingredient_last(self):
        pantry = build_pantry_urgency_map(self.user)
        self.assertEqual(len(pantry), 0)
        UserProduct.objects.create(
            user=self.user,
            catalog_product=self.catalog_milk,
            add_method=AddMethod.BARCODE,
            status=ProductStatus.ACTIVE,
            quantity=1,
            expiry_date=date.today() + timedelta(days=3),
        )
        pantry = build_pantry_urgency_map(self.user)
        s_both = score_recipe(self.r_both, pantry)
        self.assertFalse(s_both.all_required_matched)
        s_milk = score_recipe(self.r_milk_only, pantry)
        self.assertTrue(s_milk.all_required_matched)

    def test_manual_category_fallback(self):
        ing = Ingredient.objects.create(slug="tomato", name_es="Tomate", name_en="Tomato", category=Category.VEGETABLES)
        CategoryIngredientDefault.objects.create(category=Category.VEGETABLES, ingredient=ing)
        r = Recipe.objects.create(title_es="Ensalada", steps_es="Cortar.", is_published=True)
        RecipeIngredient.objects.create(recipe=r, ingredient=ing, required=True)

        UserProduct.objects.create(
            user=self.user,
            catalog_product=None,
            name_override="tomates cherry",
            manual_category=Category.VEGETABLES,
            add_method=AddMethod.MANUAL,
            status=ProductStatus.ACTIVE,
            quantity=1,
            expiry_date=date.today() + timedelta(days=2),
        )
        pantry = build_pantry_urgency_map(self.user)
        self.assertIn(ing.id, pantry)
        s = score_recipe(r, pantry)
        self.assertTrue(s.all_required_matched)
        self.assertEqual(s.urgency_days, 2)


class RecipeAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="apiuser",
            email="api@test.com",
            password="test-pass-123",
        )
        self.client.force_authenticate(user=self.user)
        self.milk = Ingredient.objects.create(slug="milk", name_es="Leche", name_en="Milk")
        self.r = Recipe.objects.create(title_es="Test", steps_es="Pasos.", is_published=True)
        RecipeIngredient.objects.create(recipe=self.r, ingredient=self.milk, required=True)

    def test_list_requires_auth(self):
        self.client.force_authenticate(user=None)
        res = self.client.get("/api/recipes/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_empty_pantry_shows_missing(self):
        res = self.client.get("/api/recipes/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        row = res.data[0]
        self.assertFalse(row["all_required_matched"])
        self.assertEqual(len(row["missing_required"]), 1)

    def test_user_product_filter_not_found(self):
        import uuid

        res = self.client.get(f"/api/recipes/?user_product_id={uuid.uuid4()}")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail(self):
        res = self.client.get(f"/api/recipes/{self.r.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title_es"], "Test")


class RecipeAIGenerateTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="aiuser",
            email="ai@test.com",
            password="test-pass-123",
        )
        self.client.force_authenticate(user=self.user)
        self.milk = Ingredient.objects.create(slug="milk", name_es="Leche", name_en="Milk")
        self.sugar = Ingredient.objects.create(slug="sugar", name_es="Azúcar", name_en="Sugar")
        self.catalog_milk = ProductCatalog.objects.create(barcode="ai-milk", category=Category.DAIRY)
        ProductCatalogIngredient.objects.create(catalog_product=self.catalog_milk, ingredient=self.milk)
        self.up = UserProduct.objects.create(
            user=self.user,
            catalog_product=self.catalog_milk,
            add_method=AddMethod.BARCODE,
            status=ProductStatus.ACTIVE,
            quantity=1,
        )

    def _sample_payload(self) -> GeneratedRecipePayload:
        return GeneratedRecipePayload(
            title_es="Flan",
            title_en="Custard",
            steps_es="Mezclar y cuajar.",
            steps_en="Mix and set.",
            prep_minutes=20,
            ingredients=[
                IngredientLine(
                    slug="milk",
                    name_es="Leche",
                    name_en="Milk",
                    required=True,
                    quantity_note="500 ml",
                ),
                IngredientLine(
                    slug="sugar",
                    name_es="Azúcar",
                    name_en="Sugar",
                    required=True,
                    quantity_note="80 g",
                ),
            ],
        )

    @override_settings(OPENAI_API_KEY="")
    def test_generate_503_when_key_missing(self):
        res = self.client.post(
            "/api/recipes/generate-for-product/",
            {"user_product_id": str(self.up.id), "only_if_empty": False},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @patch("apps.recipes.services.ai_recipe_service.generate_recipe_payload")
    def test_generate_creates_recipe(self, mock_gen):
        mock_gen.return_value = self._sample_payload()
        res = self.client.post(
            "/api/recipes/generate-for-product/",
            {"user_product_id": str(self.up.id), "only_if_empty": True},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.data["created"])
        self.assertEqual(res.data["recipe"]["title"], "Flan")
        r = Recipe.objects.get(id=res.data["recipe"]["id"])
        self.assertTrue(r.ai_generated)
        self.assertTrue(r.is_published)

    @patch("apps.recipes.services.ai_recipe_service.generate_recipe_payload")
    def test_skip_when_matching_recipes_exist(self, mock_gen):
        existing = Recipe.objects.create(
            title_es="Ya existe", steps_es="Pasos.", is_published=True, ai_generated=False
        )
        RecipeIngredient.objects.create(recipe=existing, ingredient=self.milk, required=True)

        res = self.client.post(
            "/api/recipes/generate-for-product/",
            {"user_product_id": str(self.up.id), "only_if_empty": True},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.data["created"])
        mock_gen.assert_not_called()
        self.assertIn(str(existing.id), res.data["recipe_ids"])
