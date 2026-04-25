from datetime import date, timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.choices import Category
from apps.pantry.choices import AddMethod, ProductStatus, Storage
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

    def test_list_products_filter_by_storage(self):
        UserProduct.objects.create(
            user=self.user,
            add_method=AddMethod.BARCODE,
            status=ProductStatus.ACTIVE,
            storage=Storage.PANTRY,
        )
        UserProduct.objects.create(
            user=self.user,
            add_method=AddMethod.BARCODE,
            status=ProductStatus.ACTIVE,
            storage=Storage.FRIDGE,
        )
        res = self.client.get("/api/pantry/products/", {"storage": "pantry"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["storage"], "pantry")

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
        r2 = self.client.get(
            "/api/pantry/shelf-hint/",
            {"category": "cereals", "storage": "pantry"},
        )
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertEqual(r2.data["storage"], "pantry")
        self.assertEqual(
            r2.data["suggested_days"],
            suggest_days(category="cereals", storage="pantry"),
        )

    def test_create_manual_respects_storage_freezer(self):
        res = self.client.post(
            "/api/pantry/products/",
            {
                "add_method":      AddMethod.MANUAL,
                "name_override":   "Helado",
                "manual_category": Category.OTHER,
                "quantity":        1,
                "storage":         "freezer",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["storage"], "freezer")
        self.assertTrue(res.data["is_frozen"])
        self.assertIsNotNone(res.data["expiry_date"])

    def test_create_allows_total_pieces_above_units_in_pack(self):
        res = self.client.post(
            "/api/pantry/products/",
            {
                "add_method":        AddMethod.MANUAL,
                "name_override":     "Yogur",
                "manual_category":   Category.DAIRY,
                "quantity":          12,
                "units_in_pack":     3,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["quantity"], 12)
        self.assertEqual(res.data["units_in_pack"], 3)

    def test_consume_full_no_body_marks_consumed(self):
        p = UserProduct.objects.create(
            user=self.user,
            add_method=AddMethod.BARCODE,
            status=ProductStatus.ACTIVE,
            quantity=5,
            storage=Storage.FRIDGE,
        )
        r = self.client.post(f"/api/pantry/products/{p.id}/consume/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        p.refresh_from_db()
        self.assertEqual(p.status, ProductStatus.CONSUMED)
        self.assertEqual(p.quantity, 0)
        self.assertIsNotNone(p.consumed_at)

    def test_consume_partial_reduces_quantity(self):
        p = UserProduct.objects.create(
            user=self.user,
            add_method=AddMethod.BARCODE,
            status=ProductStatus.ACTIVE,
            quantity=5,
            storage=Storage.FRIDGE,
        )
        r = self.client.post(
            f"/api/pantry/products/{p.id}/consume/",
            {"amount": 2},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["status"], "active")
        self.assertEqual(r.data["quantity"], 3)
        p.refresh_from_db()
        self.assertEqual(p.quantity, 3)
        self.assertEqual(p.status, ProductStatus.ACTIVE)

    def test_consume_amount_exceeds_quantity_400(self):
        p = UserProduct.objects.create(
            user=self.user,
            add_method=AddMethod.BARCODE,
            status=ProductStatus.ACTIVE,
            quantity=2,
            storage=Storage.FRIDGE,
        )
        r = self.client.post(
            f"/api/pantry/products/{p.id}/consume/",
            {"amount": 5},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_consume_amount_equals_quantity_consumes(self):
        p = UserProduct.objects.create(
            user=self.user,
            add_method=AddMethod.BARCODE,
            status=ProductStatus.ACTIVE,
            quantity=3,
            storage=Storage.FRIDGE,
        )
        r = self.client.post(
            f"/api/pantry/products/{p.id}/consume/",
            {"amount": 3},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        p.refresh_from_db()
        self.assertEqual(p.status, ProductStatus.CONSUMED)
        self.assertEqual(p.quantity, 0)

    def test_split_creates_line_and_shrinks_source(self):
        p = UserProduct.objects.create(
            user=self.user,
            add_method=AddMethod.BARCODE,
            status=ProductStatus.ACTIVE,
            quantity=4,
            storage=Storage.FRIDGE,
        )
        r = self.client.post(
            f"/api/pantry/products/{p.id}/split/",
            {
                "take_quantity": 2,
                "storage":       "freezer",
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        p.refresh_from_db()
        self.assertEqual(p.quantity, 2)
        self.assertEqual(p.status, ProductStatus.ACTIVE)
        new_id = r.data["created"]["id"]
        n = UserProduct.objects.get(pk=new_id)
        self.assertEqual(n.quantity, 2)
        self.assertEqual(n.storage, Storage.FREEZER)

    def test_split_removes_source_when_all_moved(self):
        p = UserProduct.objects.create(
            user=self.user,
            add_method=AddMethod.BARCODE,
            status=ProductStatus.ACTIVE,
            quantity=1,
            storage=Storage.FRIDGE,
        )
        r = self.client.post(
            f"/api/pantry/products/{p.id}/split/",
            {"take_quantity": 1, "storage": "pantry"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        p.refresh_from_db()
        self.assertEqual(p.status, ProductStatus.REMOVED)
