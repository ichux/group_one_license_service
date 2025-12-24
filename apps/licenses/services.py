import secrets
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from django.utils import timezone

from apps.licenses.repositories import (
    ActivationData,
    ActivationRepository,
    BrandRepository,
    LicenseData,
    LicenseKeyData,
    LicenseKeyRepository,
    LicenseRepository,
    ProductRepository,
)


class ServiceError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class NotFoundError(ServiceError):
    pass


class ValidationError(ServiceError):
    pass


class ConflictError(ServiceError):
    pass


def generate_license_key(prefix: str = "") -> str:
    key = secrets.token_hex(16).upper()
    if prefix:
        return f"{prefix}-{key[:8]}-{key[8:16]}-{key[16:24]}-{key[24:32]}"
    return f"{key[:8]}-{key[8:16]}-{key[16:24]}-{key[24:32]}"


@dataclass
class ProvisionLicenseKeyResult:
    license_key: LicenseKeyData
    licenses: list[LicenseData]


@dataclass
class LicenseStatusResult:
    license_key: str
    customer_email: str
    product_slug: str
    status: str
    is_valid: bool
    expires_at: datetime
    max_seats: int | None
    used_seats: int
    remaining_seats: int | None
    instance_activated: bool


@dataclass
class CustomerLicenseInfo:
    license_key: str
    brand_slug: str
    customer_email: str
    licenses: list[LicenseData]


class LicenseProvisioningService:
    def __init__(
        self,
        license_key_repo: LicenseKeyRepository,
        license_repo: LicenseRepository,
        product_repo: ProductRepository,
        brand_repo: BrandRepository,
    ):
        self.license_key_repo = license_key_repo
        self.license_repo = license_repo
        self.product_repo = product_repo
        self.brand_repo = brand_repo

    def provision_license_key(
        self,
        brand_id: UUID,
        customer_email: str,
        products: list[dict],
        external_reference: str | None = None,
        license_key: str | None = None,
    ) -> ProvisionLicenseKeyResult:
        brand = self.brand_repo.get_by_id(brand_id)
        if not brand:
            raise NotFoundError("brand_not_found", f"Brand {brand_id} not found")
        if not brand.is_active:
            raise ValidationError("brand_inactive", f"Brand {brand.slug} is inactive")

        if not products:
            raise ValidationError("no_products", "At least one product is required")

        for p in products:
            product = self.product_repo.get_by_id(p["product_id"])
            if not product:
                raise NotFoundError("product_not_found", f"Product {p['product_id']} not found")
            if product.brand_id != brand_id:
                raise ValidationError(
                    "product_brand_mismatch",
                    f"Product {product.slug} does not belong to brand {brand.slug}",
                )
            if not product.is_active:
                raise ValidationError("product_inactive", f"Product {product.slug} is inactive")

        key = license_key or generate_license_key(brand.slug.upper())

        existing = self.license_key_repo.get_by_key(key)
        if existing:
            raise ConflictError("key_exists", "License key already exists")

        license_key_data = self.license_key_repo.create(
            key=key,
            brand_id=brand_id,
            customer_email=customer_email,
            external_reference=external_reference,
        )

        licenses = []
        for p in products:
            product = self.product_repo.get_by_id(p["product_id"])
            default_seats = product.default_max_seats if product else None
            max_seats = p.get("max_seats", default_seats)
            license_data = self.license_repo.create(
                license_key_id=license_key_data.id,
                product_id=p["product_id"],
                expires_at=p["expires_at"],
                max_seats=max_seats,
            )
            licenses.append(license_data)

        return ProvisionLicenseKeyResult(license_key=license_key_data, licenses=licenses)

    def add_license_to_key(
        self,
        brand_id: UUID,
        license_key: str,
        product_id: UUID,
        expires_at: datetime,
        max_seats: int | None = None,
    ) -> LicenseData:
        key_data = self.license_key_repo.get_by_brand_and_key(brand_id, license_key)
        if not key_data:
            raise NotFoundError("key_not_found", "License key not found")

        product = self.product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundError("product_not_found", f"Product {product_id} not found")
        if product.brand_id != brand_id:
            raise ValidationError("product_brand_mismatch", "Product does not belong to this brand")
        if not product.is_active:
            raise ValidationError("product_inactive", f"Product {product.slug} is inactive")

        existing = self.license_repo.get_by_key_and_product(key_data.id, product_id)
        if existing:
            raise ConflictError(
                "license_exists",
                f"License for product {product.slug} already exists on this key",
            )

        final_max_seats = max_seats if max_seats is not None else product.default_max_seats
        return self.license_repo.create(
            license_key_id=key_data.id,
            product_id=product_id,
            expires_at=expires_at,
            max_seats=final_max_seats,
        )

    def get_license_key_details(
        self, brand_id: UUID, license_key: str
    ) -> ProvisionLicenseKeyResult:
        key_data = self.license_key_repo.get_by_brand_and_key(brand_id, license_key)
        if not key_data:
            raise NotFoundError("key_not_found", "License key not found")

        licenses = self.license_repo.list_by_license_key(key_data.id)
        return ProvisionLicenseKeyResult(license_key=key_data, licenses=licenses)


class LicenseActivationService:
    def __init__(
        self,
        license_key_repo: LicenseKeyRepository,
        license_repo: LicenseRepository,
        activation_repo: ActivationRepository,
        product_repo: ProductRepository,
    ):
        self.license_key_repo = license_key_repo
        self.license_repo = license_repo
        self.activation_repo = activation_repo
        self.product_repo = product_repo

    def _is_license_valid(self, license_data: LicenseData, now: datetime) -> bool:
        if license_data.status != "valid":
            return False
        return not (license_data.expires_at and license_data.expires_at < now)

    def _can_activate(self, license_data: LicenseData) -> bool:
        if license_data.max_seats is None:
            return True
        return license_data.used_seats < license_data.max_seats

    def activate(
        self,
        license_key: str,
        product_slug: str,
        instance_id: str,
        instance_name: str = "",
        ip_address: str | None = None,
        user_agent: str = "",
        now: datetime | None = None,
    ) -> ActivationData:
        now = now or timezone.now()

        key_data = self.license_key_repo.get_by_key(license_key)
        if not key_data:
            raise NotFoundError("key_not_found", "License key not found")

        product = self.product_repo.get_by_brand_and_slug(key_data.brand_id, product_slug)
        if not product:
            raise NotFoundError("product_not_found", f"Product {product_slug} not found")

        license_data = self.license_repo.get_by_key_and_product(key_data.id, product.id)
        if not license_data:
            raise NotFoundError(
                "license_not_found",
                f"No license for product {product_slug} on this key",
            )

        if not self._is_license_valid(license_data, now):
            raise ValidationError(
                "license_invalid",
                f"License is not valid (status: {license_data.status})",
            )

        existing = self.activation_repo.get_active_by_license_and_instance(
            license_data.id, instance_id
        )
        if existing:
            return existing

        if not self._can_activate(license_data):
            raise ValidationError(
                "no_seats_available",
                f"No seats available (max: {license_data.max_seats}, used: {license_data.used_seats})",
            )

        return self.activation_repo.create(
            license_id=license_data.id,
            instance_id=instance_id,
            instance_name=instance_name,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def deactivate(
        self,
        license_key: str,
        product_slug: str,
        instance_id: str,
    ) -> ActivationData:
        key_data = self.license_key_repo.get_by_key(license_key)
        if not key_data:
            raise NotFoundError("key_not_found", "License key not found")

        product = self.product_repo.get_by_brand_and_slug(key_data.brand_id, product_slug)
        if not product:
            raise NotFoundError("product_not_found", f"Product {product_slug} not found")

        license_data = self.license_repo.get_by_key_and_product(key_data.id, product.id)
        if not license_data:
            raise NotFoundError(
                "license_not_found",
                f"No license for product {product_slug} on this key",
            )

        existing = self.activation_repo.get_active_by_license_and_instance(
            license_data.id, instance_id
        )
        if not existing:
            raise NotFoundError("activation_not_found", "No active activation found")

        result = self.activation_repo.deactivate(existing.id)
        if not result:
            raise NotFoundError("activation_not_found", "Failed to deactivate")
        return result


class LicenseStatusService:
    def __init__(
        self,
        license_key_repo: LicenseKeyRepository,
        license_repo: LicenseRepository,
        activation_repo: ActivationRepository,
        product_repo: ProductRepository,
    ):
        self.license_key_repo = license_key_repo
        self.license_repo = license_repo
        self.activation_repo = activation_repo
        self.product_repo = product_repo

    def _is_license_valid(self, license_data: LicenseData, now: datetime) -> bool:
        if license_data.status != "valid":
            return False
        return not (license_data.expires_at and license_data.expires_at < now)

    def get_status(
        self,
        license_key: str,
        product_slug: str,
        instance_id: str | None = None,
        now: datetime | None = None,
    ) -> LicenseStatusResult:
        now = now or timezone.now()

        key_data = self.license_key_repo.get_by_key(license_key)
        if not key_data:
            raise NotFoundError("key_not_found", "License key not found")

        product = self.product_repo.get_by_brand_and_slug(key_data.brand_id, product_slug)
        if not product:
            raise NotFoundError("product_not_found", f"Product {product_slug} not found")

        license_data = self.license_repo.get_by_key_and_product(key_data.id, product.id)
        if not license_data:
            raise NotFoundError(
                "license_not_found",
                f"No license for product {product_slug} on this key",
            )

        is_valid = self._is_license_valid(license_data, now)

        instance_activated = False
        if instance_id:
            activation = self.activation_repo.get_active_by_license_and_instance(
                license_data.id, instance_id
            )
            instance_activated = activation is not None

        remaining = None
        if license_data.max_seats is not None:
            remaining = max(0, license_data.max_seats - license_data.used_seats)

        return LicenseStatusResult(
            license_key=license_key,
            customer_email=key_data.customer_email,
            product_slug=product_slug,
            status=license_data.status,
            is_valid=is_valid,
            expires_at=license_data.expires_at,
            max_seats=license_data.max_seats,
            used_seats=license_data.used_seats,
            remaining_seats=remaining,
            instance_activated=instance_activated,
        )


class LicenseQueryService:
    def __init__(
        self,
        license_key_repo: LicenseKeyRepository,
        license_repo: LicenseRepository,
    ):
        self.license_key_repo = license_key_repo
        self.license_repo = license_repo

    def list_by_customer_email(
        self, email: str, brand_id: UUID | None = None
    ) -> list[CustomerLicenseInfo]:
        keys = self.license_key_repo.list_by_email(email, brand_id)
        results = []
        for key in keys:
            licenses = self.license_repo.list_by_license_key(key.id)
            results.append(
                CustomerLicenseInfo(
                    license_key=key.key,
                    brand_slug=key.brand_slug,
                    customer_email=key.customer_email,
                    licenses=licenses,
                )
            )
        return results
