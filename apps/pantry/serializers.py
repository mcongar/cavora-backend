from datetime import date

from django.utils import timezone
from rest_framework import serializers

from apps.catalog.models import ProductCatalog
from apps.catalog.serializers import ProductCatalogSerializer
from .choices import Storage
from .models import UserProduct, ScanSession
from .shelf_hints import effective_category, suggested_expiry_date
from .storage_defaults import default_storage_for_category


def _validate_units_in_pack(*, units_in_pack: int | None) -> None:
    if units_in_pack is not None and units_in_pack < 1:
        raise serializers.ValidationError({"units_in_pack": "Must be at least 1 when set."})


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
            "add_method", "quantity", "unit", "units_in_pack",
            "expiry_date", "expiry_estimated",
            "manual_category", "is_frozen", "frozen_at", "storage",
            "status", "consumed_at", "wasted_at", "created_at",
        ]
        read_only_fields = [
            "id", "display_name", "is_frozen", "consumed_at", "wasted_at", "created_at",
        ]


class CreateUserProductSerializer(serializers.ModelSerializer):
    catalog_product_id = serializers.UUIDField(required=False, allow_null=True)
    is_frozen = serializers.BooleanField(required=False, write_only=True)

    class Meta:
        model = UserProduct
        fields = [
            "catalog_product_id", "name_override", "add_method",
            "quantity", "unit", "expiry_date", "expiry_estimated",
            "manual_category", "is_frozen", "frozen_at",
            "storage", "units_in_pack",
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
        if "units_in_pack" in attrs:
            _validate_units_in_pack(units_in_pack=attrs.get("units_in_pack"))
        return attrs

    def create(self, validated_data):
        legacy_frozen = validated_data.pop("is_frozen", None)
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

        if validated_data.get("storage") in ("", None):
            if legacy_frozen is True:
                validated_data["storage"] = Storage.FREEZER
            elif cat_str:
                validated_data["storage"] = default_storage_for_category(cat_str)
            else:
                validated_data["storage"] = Storage.FRIDGE
        if validated_data["storage"] == Storage.FREEZER and not validated_data.get("frozen_at"):
            validated_data["frozen_at"] = timezone.localdate()

        if validated_data.get("expiry_date") is None and cat_str:
            ref = validated_data.get("frozen_at") or timezone.localdate()
            st = validated_data["storage"]
            if st == Storage.FREEZER:
                ref = validated_data.get("frozen_at") or timezone.localdate()
            validated_data["expiry_date"] = suggested_expiry_date(
                category=cat_str,
                reference_date=ref,
                storage=st,
            )
            validated_data["expiry_estimated"] = True

        return UserProduct.objects.create(
            user=user,
            catalog_product_id=catalog_id,
            **validated_data,
        )


class UpdateUserProductSerializer(serializers.ModelSerializer):
    """`is_frozen` is a legacy input alias mapped to `storage` in validate()."""

    is_frozen = serializers.BooleanField(required=False, write_only=True)

    class Meta:
        model = UserProduct
        fields = [
            "quantity", "unit", "expiry_date", "expiry_estimated",
            "manual_category", "frozen_at", "storage", "units_in_pack", "is_frozen",
        ]

    def validate(self, attrs):
        inst = self.instance
        if inst and inst.catalog_product_id and "manual_category" in attrs:
            attrs.pop("manual_category", None)
        if "storage" in attrs:
            attrs.pop("is_frozen", None)
        elif "is_frozen" in attrs:
            attrs["storage"] = Storage.FREEZER if attrs.pop("is_frozen") else inst.storage
        if "units_in_pack" in attrs:
            _validate_units_in_pack(units_in_pack=attrs.get("units_in_pack"))
        return attrs

    def update(self, instance, validated_data):
        if instance.catalog_product_id and "manual_category" in validated_data:
            validated_data.pop("manual_category", None)
        validated_data.pop("is_frozen", None)

        storage = validated_data.get("storage", instance.storage)
        frozen_at = validated_data.get("frozen_at", instance.frozen_at)

        cat_str = effective_category(
            catalog_category=(
                instance.catalog_product.category if instance.catalog_product else None
            ),
            manual_category=validated_data.get("manual_category", instance.manual_category),
        )

        if (
            "expiry_date" not in validated_data
            and ("storage" in validated_data or "frozen_at" in validated_data)
            and cat_str
        ):
            is_fz = storage == Storage.FREEZER
            if is_fz:
                ref = frozen_at if frozen_at else date.today()
                if "frozen_at" not in validated_data and not instance.frozen_at:
                    validated_data["frozen_at"] = ref
            else:
                ref = date.today()
            validated_data["expiry_date"] = suggested_expiry_date(
                category=cat_str,
                reference_date=ref,
                storage=storage,
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
    storage = serializers.ChoiceField(choices=Storage.choices, required=False)
    frozen_at = serializers.DateField(required=False, allow_null=True)
    units_in_pack = serializers.IntegerField(required=False, min_value=1, allow_null=True)
    is_frozen = serializers.BooleanField(required=False)

    def validate(self, attrs):
        u = attrs.get("units_in_pack")
        if u is not None:
            _validate_units_in_pack(units_in_pack=u)
        return attrs


class BulkAddSerializer(serializers.Serializer):
    products = serializers.ListField(
        child=BulkProductItemSerializer(),
        min_length=1,
        max_length=100,
    )


class ConsumeProductBodySerializer(serializers.Serializer):
    """Optional body for POST /products/{id}/consume/."""

    amount = serializers.IntegerField(min_value=1, required=False, allow_null=True)


class SplitProductSerializer(serializers.Serializer):
    """Body for POST /products/{id}/split/"""

    take_quantity = serializers.IntegerField(min_value=1)
    storage = serializers.ChoiceField(choices=Storage.choices)
    frozen_at = serializers.DateField(required=False, allow_null=True)
    expiry_date = serializers.DateField(required=False, allow_null=True)
    expiry_estimated = serializers.BooleanField(default=True)

    def validate(self, attrs):
        st = attrs["storage"]
        if st == Storage.FREEZER and not attrs.get("frozen_at"):
            attrs["frozen_at"] = timezone.localdate()
        return attrs
