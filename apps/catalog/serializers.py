from rest_framework import serializers
from .models import ProductCatalog, ProductMatch


class ProductCatalogSerializer(serializers.ModelSerializer):
    name  = serializers.SerializerMethodField()
    brand = serializers.SerializerMethodField()

    class Meta:
        model = ProductCatalog
        fields = [
            "id", "barcode", "name", "brand", "category",
            "image_url", "nutri_score", "nova_group",
            "calories", "proteins", "carbs", "fats", "sugars",
            "shelf_life_days", "is_organic", "score",
        ]

    def _lang(self):
        return self.context.get("lang", "es")

    def get_name(self, obj):
        return obj.get_name(self._lang())

    def get_brand(self, obj):
        return obj.brands