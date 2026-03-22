from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from .models import ProductCatalog
from .serializers import ProductCatalogSerializer
from apps.integrations.open_food_facts import fetch_by_barcode, search_by_name, normalize
from apps.integrations.open_food_facts.mapper import normalize_language


def get_language(request) -> str:
    lang = request.headers.get("Accept-Language", "").strip()[:2]
    if not lang and request.user.is_authenticated:
        lang = getattr(request.user, "language", "es")
    return normalize_language(lang)


class BarcodeView(APIView):
    def get(self, request, code):
        lang = get_language(request)

        # 1. Check local DB by barcode
        product = ProductCatalog.objects.filter(barcode=code).first()
        if product:
            return Response(ProductCatalogSerializer(product, context={"lang": lang}).data)

        # 2. Fetch from OFF
        raw = fetch_by_barcode(code)
        if not raw:
            return Response(
                {"detail": "Product not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # 3. Normalize
        data = normalize(raw, barcode=code)
        if not data:
            return Response(
                {"detail": "Product has no usable data"},
                status=status.HTTP_404_NOT_FOUND
            )

        # 4. Deduplicate by off_id — may exist from a previous name search
        off_id = data.get("off_id", "")
        if off_id:
            product, _ = ProductCatalog.objects.update_or_create(
                off_id=off_id,
                defaults={**data, "last_synced_at": timezone.now()}
            )
        else:
            product, _ = ProductCatalog.objects.update_or_create(
                barcode=code,
                defaults={**data, "last_synced_at": timezone.now()}
            )

        return Response(ProductCatalogSerializer(product, context={"lang": lang}).data)


class ProductSearchView(APIView):
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response(
                {"detail": "Query parameter 'q' is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        lang = get_language(request)

        # Always search OFF for name queries
        raw_results = search_by_name(query, lang=lang)
        if not raw_results:
            return Response([])

        products = []
        for raw in raw_results:
            data = normalize(raw)
            if not data:
                continue

            off_id = data.get("off_id", "")
            barcode = data.get("barcode")

            if off_id:
                product, _ = ProductCatalog.objects.update_or_create(
                    off_id=off_id,
                    defaults={**data, "last_synced_at": timezone.now()}
                )
            elif barcode:
                product, _ = ProductCatalog.objects.update_or_create(
                    barcode=barcode,
                    defaults={**data, "last_synced_at": timezone.now()}
                )
            else:
                continue

            products.append(product)

        return Response(ProductCatalogSerializer(products, many=True, context={"lang": lang}).data)
