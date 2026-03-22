from rest_framework import serializers

from apps.catalog.serializers import ProductCatalogSerializer
from .models import UserProduct, ScanSession


class ScanSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScanSession
        fields = ["id", "method", "products_count", "label", "created_at"]
        read_only_fields = ["id", "products_count", "created_at"]


class UserProductSerializer(serializers.ModelSerializer):
    catalog_product = ProductCatalogSerializer(read_only=True)
    display_name = serializers.ReadOnlyField()

    class Meta:
        model = UserProduct
        fields = [
            "id", "display_name", "catalog_product", "name_override",
            "add_method", "quantity", "unit",
            "expiry_date", "expiry_estimated",
            "status", "consumed_at", "created_at",
        ]
        read_only_fields = ["id", "display_name", "consumed_at", "created_at"]


class CreateUserProductSerializer(serializers.ModelSerializer):
    catalog_product_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = UserProduct
        fields = [
            "catalog_product_id", "name_override", "add_method",
            "quantity", "unit", "expiry_date", "expiry_estimated",
        ]

    def create(self, validated_data):
        catalog_id = validated_data.pop("catalog_product_id", None)
        user = self.context["request"].user
        return UserProduct.objects.create(
            user=user,
            catalog_product_id=catalog_id,
            **validated_data
        )


class UpdateUserProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProduct
        fields = ["quantity", "unit", "expiry_date", "expiry_estimated"]


class BulkProductItemSerializer(serializers.Serializer):
    catalog_product_id = serializers.UUIDField(required=False, allow_null=True)
    name_override = serializers.CharField(required=False, allow_blank=True)
    quantity = serializers.IntegerField(default=1, min_value=1)
    unit = serializers.CharField(required=False, allow_blank=True)
    expiry_date = serializers.DateField(required=False, allow_null=True)
    expiry_estimated = serializers.BooleanField(default=True)


class BulkAddSerializer(serializers.Serializer):
    products = serializers.ListField(
        child=BulkProductItemSerializer(),
        min_length=1,
        max_length=100,
    )
