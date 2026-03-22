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


class UserProductListCreateView(generics.ListCreateAPIView):
    def get_queryset(self):
        qs = UserProduct.objects.filter(
            user=self.request.user,
            status=ProductStatus.ACTIVE
        ).select_related("catalog_product")

        expiring = self.request.query_params.get("expiring")
        if expiring == "soon":
            from datetime import date, timedelta
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
