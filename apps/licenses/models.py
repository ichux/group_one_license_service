import uuid

from django.db import models
from django.utils import timezone

from apps.brands.models import Brand, Product


class LicenseKey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=64, unique=True, db_index=True)
    brand = models.ForeignKey(
        Brand,
        on_delete=models.PROTECT,
        related_name="license_keys",
    )
    customer_email = models.EmailField(db_index=True)
    external_reference = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "license_keys"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer_email"]),
            models.Index(fields=["brand", "customer_email"]),
            models.Index(fields=["external_reference"]),
        ]

    def __str__(self) -> str:
        return f"{self.key[:8]}...{self.key[-4:]}"


class LicenseStatus(models.TextChoices):
    VALID = "valid", "Valid"
    SUSPENDED = "suspended", "Suspended"
    CANCELLED = "cancelled", "Cancelled"
    EXPIRED = "expired", "Expired"


class License(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    license_key = models.ForeignKey(
        LicenseKey,
        on_delete=models.CASCADE,
        related_name="licenses",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="licenses",
    )
    status = models.CharField(
        max_length=20,
        choices=LicenseStatus.choices,
        default=LicenseStatus.VALID,
    )
    expires_at = models.DateTimeField()
    max_seats = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "licenses"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["license_key", "product"]),
            models.Index(fields=["status"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"License({self.product.slug}) - {self.status}"

    @property
    def is_valid(self) -> bool:
        if self.status != LicenseStatus.VALID:
            return False
        return not (self.expires_at and self.expires_at < timezone.now())

    @property
    def is_expired(self) -> bool:
        return bool(self.expires_at and self.expires_at < timezone.now())

    @property
    def used_seats(self) -> int:
        return self.activations.filter(is_active=True).count()

    @property
    def remaining_seats(self) -> int | None:
        if self.max_seats is None:
            return None
        return max(0, self.max_seats - self.used_seats)

    def can_activate(self) -> bool:
        if not self.is_valid:
            return False
        if self.max_seats is None:
            return True
        return self.used_seats < self.max_seats


class Activation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    license = models.ForeignKey(
        License,
        on_delete=models.CASCADE,
        related_name="activations",
    )
    instance_id = models.CharField(max_length=500)
    instance_name = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    activated_at = models.DateTimeField(auto_now_add=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        db_table = "activations"
        ordering = ["-activated_at"]
        indexes = [
            models.Index(fields=["license", "instance_id"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["instance_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["license", "instance_id"],
                condition=models.Q(is_active=True),
                name="unique_active_activation",
            )
        ]

    def __str__(self) -> str:
        status = "Active" if self.is_active else "Inactive"
        return f"Activation({self.instance_id[:30]}) - {status}"


class AuditAction(models.TextChoices):
    LICENSE_KEY_CREATED = "license_key_created", "License Key Created"
    LICENSE_CREATED = "license_created", "License Created"
    LICENSE_RENEWED = "license_renewed", "License Renewed"
    LICENSE_SUSPENDED = "license_suspended", "License Suspended"
    LICENSE_RESUMED = "license_resumed", "License Resumed"
    LICENSE_CANCELLED = "license_cancelled", "License Cancelled"
    ACTIVATION_CREATED = "activation_created", "Activation Created"
    ACTIVATION_DEACTIVATED = "activation_deactivated", "Activation Deactivated"


class ActorType(models.TextChoices):
    BRAND = "brand", "Brand System"
    PRODUCT = "product", "End-User Product"
    CUSTOMER = "customer", "Customer"
    SYSTEM = "system", "System"
    ADMIN = "admin", "Administrator"


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    license = models.ForeignKey(
        License,
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_logs",
    )
    license_key = models.ForeignKey(
        LicenseKey,
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=50, choices=AuditAction.choices)
    actor_type = models.CharField(max_length=20, choices=ActorType.choices)
    actor_id = models.CharField(max_length=255)
    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["license"]),
            models.Index(fields=["license_key"]),
            models.Index(fields=["action"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["actor_type", "actor_id"]),
        ]

    def __str__(self) -> str:
        return f"AuditLog({self.action}) - {self.created_at}"
