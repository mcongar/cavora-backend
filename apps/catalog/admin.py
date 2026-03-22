from django.contrib import admin
from .models import ProductCatalog, ProductMatch


@admin.register(ProductCatalog)
class ProductCatalogAdmin(admin.ModelAdmin):
    list_display  = ["get_name_display", "brands", "category", "nutri_score", "nova_group", "barcode"]
    search_fields = ["name_es", "name_en", "brands", "barcode"]
    list_filter   = ["category", "nutri_score", "nova_group"]

    def get_name_display(self, obj):
        return obj.get_name()
    get_name_display.short_description = "Name"


@admin.register(ProductMatch)
class ProductMatchAdmin(admin.ModelAdmin):
    list_display  = ["raw_name", "catalog_product", "confidence", "source", "confirmed_count"]
    search_fields = ["raw_name"]
    list_filter   = ["source"]