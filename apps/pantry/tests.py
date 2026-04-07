from datetime import date, timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.choices import Category
from apps.pantry.choices import AddMethod, ProductStatus
from apps.pantry.models import UserProduct
from apps.pantry.shelf_hints import suggest_days, suggested_expiry_date
from apps.users.models import User


class DashboardStatsViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="dashuser",
            email="dash@test.com",
            password="test-pass-123",
        )
        self.client.force_authenticate(user=self.user)

    def test_dashboard_empty(self):
        res = self.client.get("/api/pantry/stats/dashboard/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["total_items"], 0)
        self.assertIsNone(res.data["pantry_avg_score"])
        self.assertIsNone(res.data["global_avg_score"])
        self.assertIsNone(res.data["consumed_avg_score"])
        self.assertEqual(res.data["wasted_count"], 0)
        self.assertEqual(res.data["expired_count"], 0)
        self.assertIsNone(res.data["waste_percent"])
        self.assertIsNone(res.data["expired_percent"])

    def test_waste_and_expired_percent_of_total(self):
        UserProduct.objects.create(
            user=self.user,
            add_method=AddMethod.BARCODE,
            status=ProductStatus.WASTED,
            expiry_date=date.today() - timedelta(days=2),
            wasted_at=timezone.now(),
        )
        UserProduct.objects.create(
            user=self.user,
            add_method=AddMethod.BARCODE,
            status=ProductStatus.CONSUMED,
            expiry_date=date.today(),
            consumed_at=timezone.now(),
        )
        res = self.client.get("/api/pantry/stats/dashboard/")
        self.assertEqual(res.data["total_items"], 2)
        self.assertEqual(res.data["wasted_count"], 1)
        self.assertEqual(res.data["waste_percent"], 50.0)
        self.assertIsNotNone(res.data["expired_percent"])


class WasteProductViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="wasteuser",
            email="waste@test.com",
            password="test-pass-123",
        )
        self.client.force_authenticate(user=self.user)

    def test_waste_expired_product(self):
        p = UserProduct.objects.create(
            user=self.user,
            add_method=AddMethod.BARCODE,
            status=ProductStatus.ACTIVE,
            expiry_date=date.today() - timedelta(days=1),
        )
        res = self.client.post(f"/api/pantry/products/{p.id}/waste/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        p.refresh_from_db()
        self.assertEqual(p.status, ProductStatus.WASTED)
        self.assertIsNotNone(p.wasted_at)

    def test_waste_allows_not_expired(self):
        p = UserProduct.objects.create(
            user=self.user,
            add_method=AddMethod.BARCODE,
            status=ProductStatus.ACTIVE,
            expiry_date=date.today() + timedelta(days=5),
        )
        res = self.client.post(f"/api/pantry/products/{p.id}/waste/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        p.refresh_from_db()
        self.assertEqual(p.status, ProductStatus.WASTED)

    def test_waste_allows_no_expiry_date(self):
        p = UserProduct.objects.create(
            user=self.user,
            add_method=AddMethod.BARCODE,
            status=ProductStatus.ACTIVE,
            expiry_date=None,
        )
        res = self.client.post(f"/api/pantry/products/{p.id}/waste/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        p.refresh_from_db()
        self.assertEqual(p.status, ProductStatus.WASTED)


class ManualProductAndShelfHintTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="manualuser",
            email="manual@test.com",
            password="test-pass-123",
        )
        self.client.force_authenticate(user=self.user)

    def test_create_manual_requires_category(self):
        res = self.client.post(
            "/api/pantry/products/",
            {
                "add_method":    AddMethod.MANUAL,
                "name_override": "Pollo entero",
                "quantity":      1,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_manual_sets_expiry_and_frozen(self):
        res = self.client.post(
            "/api/pantry/products/",
            {
                "add_method":      AddMethod.MANUAL,
                "name_override":   "Pollo",
                "manual_category": Category.MEAT,
                "quantity":        1,
                "is_frozen":       True,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.data["is_frozen"])
        self.assertIsNotNone(res.data["expiry_date"])
        self.assertTrue(res.data["expiry_estimated"])

    def test_shelf_hint_endpoint(self):
        res = self.client.get(
            "/api/pantry/shelf-hint/",
            {"category": "meat", "is_frozen": "true"},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["suggested_days"], suggest_days(category="meat", is_frozen=True))
        self.assertEqual(
            res.data["suggested_expiry_date"],
            suggested_expiry_date(
                category="meat",
                is_frozen=True,
                reference_date=date.today(),
            ).isoformat(),
        )
