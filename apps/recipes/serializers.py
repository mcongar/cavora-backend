from rest_framework import serializers

from .models import Recipe, RecipeIngredient


class RecipeIngredientNestedSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(source="ingredient.slug", read_only=True)
    name_es = serializers.CharField(source="ingredient.name_es", read_only=True)
    name_en = serializers.CharField(source="ingredient.name_en", read_only=True)

    class Meta:
        model = RecipeIngredient
        fields = ("slug", "name_es", "name_en", "required", "quantity_note")


class RecipeDetailSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientNestedSerializer(source="recipe_ingredients", many=True)

    class Meta:
        model = Recipe
        fields = (
            "id",
            "title_es",
            "title_en",
            "steps_es",
            "steps_en",
            "prep_minutes",
            "ai_generated",
            "ingredients",
        )


class RecipeGenerateForProductSerializer(serializers.Serializer):
    user_product_id = serializers.UUIDField()
    only_if_empty = serializers.BooleanField(default=True)
    language = serializers.ChoiceField(choices=["es", "en"], default="es")
