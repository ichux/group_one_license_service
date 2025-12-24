from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass
class LicenseKeyData:
    id: UUID
    key: str
    brand_id: UUID
    brand_slug: str
    customer_email: str
    external_reference: str | None
    created_at: datetime


@dataclass
class LicenseData:
    id: UUID
    license_key_id: UUID
    license_key: str
    product_id: UUID
    product_slug: str
    status: str
    expires_at: datetime
    max_seats: int | None
    used_seats: int
    created_at: datetime


@dataclass
class ActivationData:
    id: UUID
    license_id: UUID
    instance_id: str
    instance_name: str
    is_active: bool
    activated_at: datetime
    deactivated_at: datetime | None
    ip_address: str | None


@dataclass
class ProductData:
    id: UUID
    slug: str
    name: str
    brand_id: UUID
    default_max_seats: int | None
    is_active: bool


@dataclass
class BrandData:
    id: UUID
    slug: str
    name: str
    is_active: bool


class LicenseKeyRepository(Protocol):
    def create(
        self,
        key: str,
        brand_id: UUID,
        customer_email: str,
        external_reference: str | None = None,
    ) -> LicenseKeyData: ...

    def get_by_key(self, key: str) -> LicenseKeyData | None: ...

    def get_by_id(self, id: UUID) -> LicenseKeyData | None: ...

    def get_by_brand_and_key(self, brand_id: UUID, key: str) -> LicenseKeyData | None: ...

    def list_by_email(self, email: str, brand_id: UUID | None = None) -> list[LicenseKeyData]: ...


class LicenseRepository(Protocol):
    def create(
        self,
        license_key_id: UUID,
        product_id: UUID,
        expires_at: datetime,
        max_seats: int | None = None,
    ) -> LicenseData: ...

    def get_by_id(self, id: UUID) -> LicenseData | None: ...

    def get_by_key_and_product(
        self, license_key_id: UUID, product_id: UUID
    ) -> LicenseData | None: ...

    def list_by_license_key(self, license_key_id: UUID) -> list[LicenseData]: ...

    def update_status(self, id: UUID, status: str) -> LicenseData | None: ...


class ActivationRepository(Protocol):
    def create(
        self,
        license_id: UUID,
        instance_id: str,
        instance_name: str = "",
        ip_address: str | None = None,
        user_agent: str = "",
    ) -> ActivationData: ...

    def get_active_by_license_and_instance(
        self, license_id: UUID, instance_id: str
    ) -> ActivationData | None: ...

    def count_active_by_license(self, license_id: UUID) -> int: ...

    def deactivate(self, id: UUID) -> ActivationData | None: ...


class ProductRepository(Protocol):
    def get_by_id(self, id: UUID) -> ProductData | None: ...

    def get_by_brand_and_slug(self, brand_id: UUID, slug: str) -> ProductData | None: ...


class BrandRepository(Protocol):
    def get_by_id(self, id: UUID) -> BrandData | None: ...

    def get_by_slug(self, slug: str) -> BrandData | None: ...
