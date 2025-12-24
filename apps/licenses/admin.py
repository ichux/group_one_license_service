from django.contrib import admin

from .models import Activation, AuditLog, License, LicenseKey


@admin.register(LicenseKey)
class LicenseKeyAdmin(admin.ModelAdmin):
    list_display = ["key", "brand", "customer_email", "created_at"]
    list_filter = ["brand", "created_at"]
    search_fields = ["key", "customer_email", "external_reference"]
    readonly_fields = ["id", "key", "created_at", "updated_at"]
    raw_id_fields = ["brand"]


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = ["id", "license_key", "product", "status", "expires_at", "max_seats"]
    list_filter = ["status", "product__brand", "created_at", "expires_at"]
    search_fields = ["license_key__key", "license_key__customer_email"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["license_key", "product"]


@admin.register(Activation)
class ActivationAdmin(admin.ModelAdmin):
    list_display = ["id", "license", "instance_id", "is_active", "activated_at"]
    list_filter = ["is_active", "activated_at"]
    search_fields = ["instance_id", "instance_name", "license__license_key__key"]
    readonly_fields = ["id", "activated_at"]
    raw_id_fields = ["license"]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["action", "actor_type", "actor_id", "license_key", "created_at"]
    list_filter = ["action", "actor_type", "created_at"]
    search_fields = ["actor_id", "license_key__key"]
    readonly_fields = [
        "id",
        "license",
        "license_key",
        "action",
        "actor_type",
        "actor_id",
        "details",
        "ip_address",
        "created_at",
    ]
    raw_id_fields = ["license", "license_key"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
