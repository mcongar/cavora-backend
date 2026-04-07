from datetime import date

from django.utils import timezone
from rest_framework import serializers

from apps.catalog.models import ProductCatalog
from apps.catalog.serializers import ProductCatalogSerializer
from .models import UserProduct, ScanSession
from .shelf_hints import effective_category, suggested_expiry_date


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
            "manual_category", "is_frozen", "frozen_at",
            "status", "consumed_at", "wasted_at", "created_at",
        ]
        read_only_fields = ["id", "display_name", "consumed_at", "wasted_at", "created_at"]


class CreateUserProductSerializer(serializers.ModelSerializer):
    catalog_product_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = UserProduct
        fields = [
            "catalog_product_id", "name_override", "add_method",
            "quantity", "unit", "expiry_date", "expiry_estimated",
            "manual_category", "is_frozen", "frozen_at",
        ]

    def validate(self, attrs):
        catalog_id = attrs.get("catalog_product_id")
        name = (attrs.get("name_override") or "").strip()
        manual_cat = attrs.get("manual_category")

        if catalog_id is None:
            if not name:
                raise serializers.ValidationError(
                    {"name_override": "Required when no catalog product is selected."}
                )
            if not manual_cat:
                raise serializers.ValidationError(
                    {"manual_category": "Required for manual products without a catalog match."}
                )
        return attrs

    def create(self, validated_data):
        catalog_id = validated_data.pop("catalog_product_id", None)
        user = self.context["request"].user

        if catalog_id:
            validated_data.pop("manual_category", None)
            cat_str = (
                ProductCatalog.objects.filter(pk=catalog_id)
                .values_list("category", flat=True)
                .first()
            )
        else:
            cat_str = validated_data.get("manual_category")

        if validated_data.get("expiry_date") is None and cat_str:
            ref = validated_data.get("frozen_at") or timezone.localdate()
            is_fz = validated_data.get("is_frozen", False)
            validated_data["expiry_date"] = suggested_expiry_date(
                category=cat_str,
                is_frozen=is_fz,
                reference_date=ref,
            )
            validated_data["expiry_estimated"] = True

        return UserProduct.objects.create(
            user=user,
            catalog_product_id=catalog_id,
            **validated_data,
        )


class UpdateUserProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProduct
        fields = [
            "quantity", "unit", "expiry_date", "expiry_estimated",
            "manual_category", "is_frozen", "frozen_at",
        ]

    def validate(self, attrs):
        inst = self.instance
        if inst and inst.catalog_product_id and "manual_category" in attrs:
            attrs.pop("manual_category", None)
        return attrs

    def update(self, instance, validated_data):
        if instance.catalog_product_id and "manual_category" in validated_data:
            validated_data.pop("manual_category", None)

        is_frozen = validated_data.get("is_frozen", instance.is_frozen)
        frozen_at = validated_data.get("frozen_at", instance.frozen_at)

        cat_str = effective_category(
            catalog_category=(
                instance.catalog_product.category if instance.catalog_product else None
            ),
            manual_category=validated_data.get("manual_category", instance.manual_category),
        )

        if (
            "expiry_date" not in validated_data
            and ("is_frozen" in validated_data or "frozen_at" in validated_data)
            and cat_str
        ):
            ref = frozen_at if is_frozen and frozen_at else date.today()
            validated_data["expiry_date"] = suggested_expiry_date(
                category=cat_str,
                is_frozen=is_frozen,
                reference_date=ref,
            )
            validated_data["expiry_estimated"] = True

        return super().update(instance, validated_data)


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
