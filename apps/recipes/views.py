from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.pantry.models import UserProduct

from apps.recipes.models import Ingredient, Recipe
from apps.recipes.serializers import RecipeDetailSerializer, RecipeGenerateForProductSerializer
from apps.recipes.services.ai_recipe_generator import AiRecipeGenerationError, OpenAINotConfiguredError
from apps.recipes.services.ai_recipe_service import generate_and_save_for_user_product
from apps.recipes.services.pantry_recipe_ranking import (
    rank_recipes_for_user,
    recipe_ids_for_user_product_line,
)


def _lang(request) -> str:
    h = request.headers.get("Accept-Language", "es")
    return (h[:2] if len(h) >= 2 else "es").lower()


def _title(recipe: Recipe, lang: str) -> str:
    if lang == "en" and recipe.title_en:
        return recipe.title_en
    return recipe.title_es


def _serialize_list_item(recipe: Recipe, score, pantry, lang: str) -> dict:
    missing_detail = []
    for slug in score.missing_required_slugs:
        ing = Ingredient.objects.filter(slug=slug).first()
        if ing:
            missing_detail.append(
                {
                    "slug": ing.slug,
                    "name": ing.name_es if lang != "en" else (ing.name_en or ing.name_es),
                }
            )
        else:
            missing_detail.append({"slug": slug, "name": slug})

    matched = []
    for ri in recipe.recipe_ingredients.all():
        if ri.required and ri.ingredient_id in pantry:
            ing = ri.ingredient
            matched.append(
                {
                    "slug": ing.slug,
                    "name": ing.name_es if lang != "en" else (ing.name_en or ing.name_es),
                }
            )

    return {
        "id": recipe.id,
        "title": _title(recipe, lang),
        "prep_minutes": recipe.prep_minutes,
        "urgency_days": score.urgency_days,
        "all_required_matched": score.all_required_matched,
        "has_unknown_expiry_in_match": score.has_unknown_expiry_in_match,
        "missing_required": missing_detail,
        "matched_ingredients": matched,
    }


class RecipeListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Recipe.objects.filter(is_published=True)
        user_product_id = request.query_params.get("user_product_id")
        if user_product_id:
            ids = recipe_ids_for_user_product_line(request.user, user_product_id)
            if ids is None:
                return Response({"detail": "User product not found."}, status=status.HTTP_404_NOT_FOUND)
            qs = qs.filter(id__in=ids)
        qs = qs.prefetch_related("recipe_ingredients__ingredient")
        ranked, pantry = rank_recipes_for_user(request.user, qs)
        lang = _lang(request)
        data = [_serialize_list_item(r, s, pantry, lang) for r, s in ranked]
        return Response(data)


class RecipeDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RecipeDetailSerializer
    queryset = Recipe.objects.filter(is_published=True).prefetch_related("recipe_ingredients__ingredient")

    def get_object(self):
        return get_object_or_404(Recipe, id=self.kwargs["pk"], is_published=True)


class RecipeGenerateForProductView(APIView):
    """
    POST: generate one published recipe anchored on the pantry line's ingredients.
    If only_if_empty (default) and recipes already exist for that product, returns existing ids without calling OpenAI.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = RecipeGenerateForProductSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        uid = ser.validated_data["user_product_id"]
        only_if_empty = ser.validated_data["only_if_empty"]
        language = ser.validated_data["language"]
        lang = "en" if language == "en" else "es"

        try:
            skipped, recipe, existing_ids = generate_and_save_for_user_product(
                request.user,
                uid,
                only_if_empty=only_if_empty,
                language=language,
            )
        except UserProduct.DoesNotExist:
            return Response({"detail": "User product not found."}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except OpenAINotConfiguredError as e:
            return Response({"detail": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except AiRecipeGenerationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        if skipped and existing_ids:
            return Response(
                {
                    "created": False,
                    "reason": "matching_recipes_exist",
                    "recipe_ids": [str(x) for x in existing_ids],
                },
                status=status.HTTP_200_OK,
            )

        assert recipe is not None
        qs = Recipe.objects.filter(id=recipe.id, is_published=True).prefetch_related(
            "recipe_ingredients__ingredient"
        )
        ranked, pantry = rank_recipes_for_user(request.user, qs)
        r, s = ranked[0]
        return Response(
            {
                "created": True,
                "recipe": _serialize_list_item(r, s, pantry, lang),
            },
            status=status.HTTP_201_CREATED,
        )
