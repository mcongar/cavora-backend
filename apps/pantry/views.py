from datetime import date, timedelta

from apps.catalog.choices import Category
from apps.catalog.models import ProductCatalog
from django.db import transaction
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .choices import Storage
from .models import UserProduct, ScanSession, ProductStatus
from .serializers import (
    UserProductSerializer,
    CreateUserProductSerializer,
    UpdateUserProductSerializer,
    ScanSessionSerializer,
    BulkAddSerializer,
    SplitProductSerializer,
    ConsumeProductBodySerializer,
)
from .shelf_hints import effective_category, suggested_expiry_date, suggest_days
from .storage_defaults import default_storage_for_category


def _weighted_catalog_score(qs):
    """Quantity-weighted mean of catalog score; None if no scored rows."""
    total_w = 0
    total_s = 0.0
    for row in qs.select_related("catalog_product"):
        if not row.catalog_product:
            continue
        sc = row.catalog_product.score
        if sc is None:
            continue
        total_s += float(sc) * row.quantity
        total_w += row.quantity
    if total_w == 0:
        return None
    return round(total_s / total_w, 1)


def _count_expired_rows(user) -> int:
    """
    Rows that count as "expired" for stats (can overlap with wasted: e.g. thrown away
    after best-before still counts as both wasted and expired in aggregate totals).
    """
    today = timezone.localdate()
    n = 0
    for row in UserProduct.objects.filter(user=user).iterator():
        if row.status == ProductStatus.EXPIRED:
            n += 1
            continue
        if row.status == ProductStatus.ACTIVE and row.expiry_date and row.expiry_date < today:
            n += 1
            continue
        if row.status == ProductStatus.CONSUMED and row.expiry_date and row.consumed_at:
            if timezone.localtime(row.consumed_at).date() > row.expiry_date:
                n += 1
                continue
        if row.status == ProductStatus.WASTED and row.expiry_date and row.wasted_at:
            if timezone.localtime(row.wasted_at).date() >= row.expiry_date:
                n += 1
    return n


class UserProductListCreateView(generics.ListCreateAPIView):
    def get_queryset(self):
        qs = UserProduct.objects.filter(
            user=self.request.user,
            status=ProductStatus.ACTIVE
        ).select_related("catalog_product")

        expiring = self.request.query_params.get("expiring")
        if expiring == "soon":
            threshold = date.today() + timedelta(days=self.request.user.alert_days_before)
            qs = qs.filter(expiry_date__lte=threshold)

        storage = self.request.query_params.get("storage")
        if storage in (Storage.PANTRY, Storage.FRIDGE, Storage.FREEZER):
            qs = qs.filter(storage=storage)

        return qs

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CreateUserProductSerializer
        return UserProductSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["lang"] = self.request.user.language
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        read = UserProductSerializer(
            instance,
            context=self.get_serializer_context(),
        )
        headers = self.get_success_headers(read.data)
        return Response(read.data, status=status.HTTP_201_CREATED, headers=headers)


class UserProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    def get_queryset(self):
        return UserProduct.objects.filter(
            user=self.request.user
        ).select_related("catalog_product")

    def get_serializer_class(self):
        if self.request.method in ["PATCH", "PUT"]:
            return UpdateUserProductSerializer
        return UserProductSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["lang"] = self.request.user.language
        return context

    def perform_destroy(self, instance):
        instance.status = ProductStatus.REMOVED
        instance.save(update_fields=["status", "updated_at"])


class ConsumeProductView(APIView):
    def post(self, request, pk):
        product = generics.get_object_or_404(
            UserProduct,
            id=pk,
            user=request.user,
            status=ProductStatus.ACTIVE
        )
        ser = ConsumeProductBodySerializer(data=request.data or {})
        ser.is_valid(raise_exception=True)
        amount = ser.validated_data.get("amount")
        lang = request.user.language
        now = timezone.now()

        with transaction.atomic():
            if amount is None:
                product.status = ProductStatus.CONSUMED
                product.consumed_at = now
                product.quantity = 0
                product.save(update_fields=["status", "consumed_at", "quantity", "updated_at"])
                return Response(
                    UserProductSerializer(product, context={"lang": lang}).data
                )
            if amount > product.quantity:
                return Response(
                    {"amount": f"Cannot consume {amount} pieces; only {product.quantity} on this line."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if amount < product.quantity:
                product.quantity -= amount
                product.save(update_fields=["quantity", "updated_at"])
            else:
                product.status = ProductStatus.CONSUMED
                product.consumed_at = now
                product.quantity = 0
                product.save(update_fields=["status", "consumed_at", "quantity", "updated_at"])
            return Response(
                UserProductSerializer(product, context={"lang": lang}).data
            )


class WasteProductView(APIView):
    """Mark a pantry line as thrown away (waste), regardless of best-before date."""

    def post(self, request, pk):
        product = generics.get_object_or_404(
            UserProduct,
            id=pk,
            user=request.user,
            status=ProductStatus.ACTIVE,
        )
        now = timezone.now()
        product.status = ProductStatus.WASTED
        product.wasted_at = now
        product.save(update_fields=["status", "wasted_at", "updated_at"])
        return Response(
            UserProductSerializer(product, context={"lang": request.user.language}).data
        )


class ScanSessionCreateView(generics.CreateAPIView):
    serializer_class = ScanSessionSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class BulkAddView(APIView):
    def post(self, request, pk):
        session = generics.get_object_or_404(
            ScanSession,
            id=pk,
            user=request.user
        )

        serializer = BulkAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        products_data = serializer.validated_data["products"]

        with transaction.atomic():
            created = []
            for item in products_data:
                cat_id = item.get("catalog_product_id")
                cat_str = None
                if cat_id:
                    cat_str = (
                        ProductCatalog.objects.filter(pk=cat_id)
                        .values_list("category", flat=True)
                        .first()
                    )
                st = item.get("storage")
                if not st:
                    if item.get("is_frozen"):
                        st = Storage.FREEZER
                    elif cat_str:
                        st = default_storage_for_category(cat_str)
                    else:
                        st = Storage.FRIDGE
                exp = item.get("expiry_date")
                exp_est = item.get("expiry_estimated", True)
                ref = item.get("frozen_at")
                if st == Storage.FREEZER and not ref:
                    ref = timezone.localdate()
                if exp is None and cat_str:
                    r = ref or timezone.localdate()
                    exp = suggested_expiry_date(
                        category=cat_str,
                        reference_date=r,
                        storage=st,
                    )
                    exp_est = True
                product = UserProduct.objects.create(
                    user=request.user,
                    session=session,
                    add_method=session.method,
                    catalog_product_id=cat_id,
                    name_override=item.get("name_override", ""),
                    quantity=item.get("quantity", 1),
                    unit=item.get("unit", ""),
                    expiry_date=exp,
                    expiry_estimated=exp_est,
                    storage=st,
                    units_in_pack=item.get("units_in_pack"),
                    frozen_at=ref if st == Storage.FREEZER else (item.get("frozen_at") or None),
                )
                created.append(product)

            session.products_count = len(created)
            session.save(update_fields=["products_count", "updated_at"])

        return Response(
            UserProductSerializer(
                created,
                many=True,
                context={"lang": request.user.language}
            ).data,
            status=status.HTTP_201_CREATED
        )


class SessionRollbackView(APIView):
    def delete(self, request, pk):
        session = generics.get_object_or_404(
            ScanSession,
            id=pk,
            user=request.user
        )
        count = UserProduct.objects.filter(
            session=session,
            status=ProductStatus.ACTIVE
        ).update(status=ProductStatus.REMOVED)

        return Response({"removed": count})


class DashboardStatsView(APIView):
    """Home screen: score averages (pantry / global / consumed) and waste vs expired shares."""

    def get(self, request):
        user = request.user

        pantry_qs = UserProduct.objects.filter(
            user=user, status=ProductStatus.ACTIVE
        )
        global_qs = UserProduct.objects.filter(user=user).exclude(
            status=ProductStatus.REMOVED
        )
        consumed_qs = UserProduct.objects.filter(
            user=user,
            status=ProductStatus.CONSUMED,
        )

        pantry_avg = _weighted_catalog_score(pantry_qs)
        global_avg = _weighted_catalog_score(global_qs)
        consumed_avg = _weighted_catalog_score(consumed_qs)

        total_items = UserProduct.objects.filter(user=user).count()
        wasted_n = UserProduct.objects.filter(
            user=user, status=ProductStatus.WASTED
        ).count()
        expired_n = _count_expired_rows(user)

        waste_percent = None
        expired_percent = None
        if total_items > 0:
            waste_percent = round(100.0 * wasted_n / total_items, 1)
            expired_percent = round(100.0 * expired_n / total_items, 1)

        return Response(
            {
                "total_items": total_items,
                "pantry_avg_score": pantry_avg,
                "global_avg_score": global_avg,
                "consumed_avg_score": consumed_avg,
                "wasted_count": wasted_n,
                "expired_count": expired_n,
                "waste_percent": waste_percent,
                "expired_percent": expired_percent,
            }
        )


class ShelfHintView(APIView):
    """
    Query: ?category=meat&storage=fridge|pantry|freezer
    Legacy: ?is_frozen=true (maps to freezer vs fridge when storage omitted)
    Optional: ?reference=YYYY-MM-DD (defaults to today).
    """

    def get(self, request):
        cat = request.query_params.get("category")
        if not cat or cat not in {c.value for c in Category}:
            return Response(
                {"detail": "Invalid or missing category."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ref_str = request.query_params.get("reference")
        if ref_str:
            try:
                y, m, d = ref_str.split("-")
                ref = date(int(y), int(m), int(d))
            except (ValueError, AttributeError):
                ref = timezone.localdate()
        else:
            ref = timezone.localdate()

        storage = request.query_params.get("storage")
        if storage in ("pantry", "fridge", "freezer"):
            st = storage
            days = suggest_days(category=cat, storage=st)
            exp = suggested_expiry_date(
                category=cat,
                reference_date=ref,
                storage=st,
            )
            is_frozen = st == Storage.FREEZER
        else:
            raw = request.query_params.get("is_frozen", "false").lower()
            is_frozen = raw in ("1", "true", "yes")
            st = "freezer" if is_frozen else "fridge"
            days = suggest_days(category=cat, is_frozen=is_frozen)
            exp = suggested_expiry_date(
                category=cat,
                reference_date=ref,
                is_frozen=is_frozen,
            )

        return Response(
            {
                "category":            cat,
                "storage":             st,
                "is_frozen":            is_frozen,
                "suggested_days":       days,
                "suggested_expiry_date": exp.isoformat(),
            }
        )


class SplitProductView(APIView):
    """Create a new line from an existing one; subtract quantity from the source (or remove it)."""

    def post(self, request, pk):
        src = generics.get_object_or_404(
            UserProduct,
            id=pk,
            user=request.user,
            status=ProductStatus.ACTIVE,
        )
        ser = SplitProductSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        n = ser.validated_data["take_quantity"]
        if n > src.quantity:
            return Response(
                {"detail": "take_quantity cannot exceed line quantity."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        st: str = ser.validated_data["storage"]
        with transaction.atomic():
            ref = ser.validated_data.get("frozen_at")
            if st == Storage.FREEZER and not ref:
                ref = timezone.localdate()
            exp = ser.validated_data.get("expiry_date")
            exp_est = ser.validated_data.get("expiry_estimated", True)
            if exp is None:
                cat_str = effective_category(
                    catalog_category=src.catalog_product.category if src.catalog_product else None,
                    manual_category=src.manual_category,
                )
                if cat_str:
                    r = (ref or timezone.localdate()) if st == Storage.FREEZER else date.today()
                    exp = suggested_expiry_date(
                        category=cat_str,
                        reference_date=r,
                        storage=st,
                    )
                    exp_est = True
            new = UserProduct(
                user=request.user,
                session=src.session,
                catalog_product=src.catalog_product,
                name_override=src.name_override,
                add_method=src.add_method,
                quantity=n,
                unit=src.unit,
                units_in_pack=src.units_in_pack,
                expiry_date=exp,
                expiry_estimated=exp_est,
                manual_category=src.manual_category,
                storage=st,
            )
            if st == Storage.FREEZER:
                new.frozen_at = ref or timezone.localdate()
            new.save()

            src.quantity = src.quantity - n
            if src.quantity < 1:
                src.status = ProductStatus.REMOVED
            src.save()
            lang = request.user.language
            return Response(
                {
                    "source":  UserProductSerializer(src, context={"lang": lang}).data,
                    "created": UserProductSerializer(new, context={"lang": lang}).data,
                },
                status=status.HTTP_201_CREATED,
            )
