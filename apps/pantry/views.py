from datetime import date, timedelta

from apps.catalog.choices import Category
from django.db import transaction
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import UserProduct, ScanSession, ProductStatus
from .serializers import (
    UserProductSerializer,
    CreateUserProductSerializer,
    UpdateUserProductSerializer,
    ScanSessionSerializer,
    BulkAddSerializer,
)
from .shelf_hints import suggested_expiry_date, suggest_days


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

        return qs

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CreateUserProductSerializer
        return UserProductSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["lang"] = self.request.user.language
        return context


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
        product.status = ProductStatus.CONSUMED
        product.consumed_at = timezone.now()
        product.save(update_fields=["status", "consumed_at", "updated_at"])
        return Response(
            UserProductSerializer(product, context={"lang": request.user.language}).data
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
                product = UserProduct.objects.create(
                    user=request.user,
                    session=session,
                    add_method=session.method,
                    catalog_product_id=item.get("catalog_product_id"),
                    name_override=item.get("name_override", ""),
                    quantity=item.get("quantity", 1),
                    unit=item.get("unit", ""),
                    expiry_date=item.get("expiry_date"),
                    expiry_estimated=item.get("expiry_estimated", True),
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
    Query: ?category=meat&is_frozen=true
    Optional: ?reference=YYYY-MM-DD (defaults to today).
    """

    def get(self, request):
        cat = request.query_params.get("category")
        if not cat or cat not in {c.value for c in Category}:
            return Response(
                {"detail": "Invalid or missing category."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        raw = request.query_params.get("is_frozen", "false").lower()
        is_frozen = raw in ("1", "true", "yes")
        ref_str = request.query_params.get("reference")
        if ref_str:
            try:
                y, m, d = ref_str.split("-")
                ref = date(int(y), int(m), int(d))
            except (ValueError, AttributeError):
                ref = timezone.localdate()
        else:
            ref = timezone.localdate()
        days = suggest_days(category=cat, is_frozen=is_frozen)
        exp = suggested_expiry_date(category=cat, is_frozen=is_frozen, reference_date=ref)
        return Response(
            {
                "category": cat,
                "is_frozen": is_frozen,
                "suggested_days": days,
                "suggested_expiry_date": exp.isoformat(),
            }
        )
