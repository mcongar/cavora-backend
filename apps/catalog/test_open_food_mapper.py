"""Tests for OFF category priority + shelf (no DB)."""

from django.test import SimpleTestCase

from apps.catalog.choices import Category
from apps.integrations.open_food_facts.mapper import (
    map_category,
    resolve_category_and_shelf_life,
)


class OpenFoodFactsMapperTests(SimpleTestCase):
    def test_spices_win_over_beverages_any_order(self):
        tags = ["en:beverages", "en:plant-based-foods-and-beverages", "en:spices"]
        cat, days = resolve_category_and_shelf_life(tags)
        self.assertEqual(cat, Category.CONDIMENTS)
        self.assertEqual(days, 730)

        tags2 = ["en:spices", "en:beverages"]
        self.assertEqual(resolve_category_and_shelf_life(tags2)[0], Category.CONDIMENTS)

    def test_sodas_beats_generic_beverage(self):
        tags = ["en:beverages", "en:sodas"]
        cat, _days = resolve_category_and_shelf_life(tags)
        self.assertEqual(cat, Category.BEVERAGES)

    def test_empty_tags_other(self):
        cat, days = resolve_category_and_shelf_life([])
        self.assertEqual(cat, Category.OTHER)
        self.assertEqual(days, 30)

    def test_map_category_compat(self):
        self.assertEqual(
            map_category(["en:cheeses"]),
            Category.DAIRY,
        )
