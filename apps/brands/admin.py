from django.contrib import admin

from .models import Brand, Product


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "slug"]
    readonly_fields = ["id", "created_at", "updated_at"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "brand", "slug", "is_active", "default_max_seats", "created_at"]
    list_filter = ["brand", "is_active", "created_at"]
    search_fields = ["name", "slug", "brand__name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    prepopulated_fields = {"slug": ("name",)}
