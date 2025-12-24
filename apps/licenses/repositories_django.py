from datetime import datetime
from uuid import UUID

from django.utils import timezone

from apps.brands.models import Brand, Product
from apps.licenses.models import Activation, License, LicenseKey, LicenseStatus
from apps.licenses.repositories import (
    ActivationData,
    BrandData,
    LicenseData,
    LicenseKeyData,
    ProductData,
)


class DjangoLicenseKeyRepository:
    def _to_data(self, obj: LicenseKey) -> LicenseKeyData:
        return LicenseKeyData(
            id=obj.id,
            key=obj.key,
            brand_id=obj.brand_id,
            brand_slug=obj.brand.slug,
            customer_email=obj.customer_email,
            external_reference=obj.external_reference,
            created_at=obj.created_at,
        )

    def create(
        self,
        key: str,
        brand_id: UUID,
        customer_email: str,
        external_reference: str | None = None,
    ) -> LicenseKeyData:
        obj = LicenseKey.objects.create(
            key=key,
            brand_id=brand_id,
            customer_email=customer_email,
            external_reference=external_reference,
        )
        return self._to_data(obj)

    def get_by_key(self, key: str) -> LicenseKeyData | None:
        try:
            obj = LicenseKey.objects.select_related("brand").get(key=key)
            return self._to_data(obj)
        except LicenseKey.DoesNotExist:
            return None

    def get_by_id(self, id: UUID) -> LicenseKeyData | None:
        try:
            obj = LicenseKey.objects.select_related("brand").get(id=id)
            return self._to_data(obj)
        except LicenseKey.DoesNotExist:
            return None

    def get_by_brand_and_key(self, brand_id: UUID, key: str) -> LicenseKeyData | None:
        try:
            obj = LicenseKey.objects.select_related("brand").get(brand_id=brand_id, key=key)
            return self._to_data(obj)
        except LicenseKey.DoesNotExist:
            return None

    def list_by_email(self, email: str, brand_id: UUID | None = None) -> list[LicenseKeyData]:
        qs = LicenseKey.objects.select_related("brand").filter(customer_email__iexact=email)
        if brand_id:
            qs = qs.filter(brand_id=brand_id)
        return [self._to_data(obj) for obj in qs]


class DjangoLicenseRepository:
    def _to_data(self, obj: License) -> LicenseData:
        return LicenseData(
            id=obj.id,
            license_key_id=obj.license_key_id,
            license_key=obj.license_key.key,
            product_id=obj.product_id,
            product_slug=obj.product.slug,
            status=obj.status,
            expires_at=obj.expires_at,
            max_seats=obj.max_seats,
            used_seats=obj.activations.filter(is_active=True).count(),
            created_at=obj.created_at,
        )

    def create(
        self,
        license_key_id: UUID,
        product_id: UUID,
        expires_at: datetime,
        max_seats: int | None = None,
    ) -> LicenseData:
        obj = License.objects.create(
            license_key_id=license_key_id,
            product_id=product_id,
            expires_at=expires_at,
            max_seats=max_seats,
            status=LicenseStatus.VALID,
        )
        return self._to_data(obj)

    def get_by_id(self, id: UUID) -> LicenseData | None:
        try:
            obj = License.objects.select_related("license_key", "product").get(id=id)
            return self._to_data(obj)
        except License.DoesNotExist:
            return None

    def get_by_key_and_product(self, license_key_id: UUID, product_id: UUID) -> LicenseData | None:
        try:
            obj = License.objects.select_related("license_key", "product").get(
                license_key_id=license_key_id, product_id=product_id
            )
            return self._to_data(obj)
        except License.DoesNotExist:
            return None

    def list_by_license_key(self, license_key_id: UUID) -> list[LicenseData]:
        qs = License.objects.select_related("license_key", "product").filter(
            license_key_id=license_key_id
        )
        return [self._to_data(obj) for obj in qs]

    def update_status(self, id: UUID, status: str) -> LicenseData | None:
        try:
            obj = License.objects.select_related("license_key", "product").get(id=id)
            obj.status = status
            obj.save(update_fields=["status", "updated_at"])
            return self._to_data(obj)
        except License.DoesNotExist:
            return None


class DjangoActivationRepository:
    def _to_data(self, obj: Activation) -> ActivationData:
        return ActivationData(
            id=obj.id,
            license_id=obj.license_id,
            instance_id=obj.instance_id,
            instance_name=obj.instance_name,
            is_active=obj.is_active,
            activated_at=obj.activated_at,
            deactivated_at=obj.deactivated_at,
            ip_address=obj.ip_address,
        )

    def create(
        self,
        license_id: UUID,
        instance_id: str,
        instance_name: str = "",
        ip_address: str | None = None,
        user_agent: str = "",
    ) -> ActivationData:
        obj = Activation.objects.create(
            license_id=license_id,
            instance_id=instance_id,
            instance_name=instance_name,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return self._to_data(obj)

    def get_active_by_license_and_instance(
        self, license_id: UUID, instance_id: str
    ) -> ActivationData | None:
        try:
            obj = Activation.objects.get(
                license_id=license_id, instance_id=instance_id, is_active=True
            )
            return self._to_data(obj)
        except Activation.DoesNotExist:
            return None

    def count_active_by_license(self, license_id: UUID) -> int:
        return Activation.objects.filter(license_id=license_id, is_active=True).count()

    def deactivate(self, id: UUID) -> ActivationData | None:
        try:
            obj = Activation.objects.get(id=id)
            obj.is_active = False
            obj.deactivated_at = timezone.now()
            obj.save(update_fields=["is_active", "deactivated_at"])
            return self._to_data(obj)
        except Activation.DoesNotExist:
            return None


class DjangoProductRepository:
    def _to_data(self, obj: Product) -> ProductData:
        return ProductData(
            id=obj.id,
            slug=obj.slug,
            name=obj.name,
            brand_id=obj.brand_id,
            default_max_seats=obj.default_max_seats,
            is_active=obj.is_active,
        )

    def get_by_id(self, id: UUID) -> ProductData | None:
        try:
            obj = Product.objects.get(id=id)
            return self._to_data(obj)
        except Product.DoesNotExist:
            return None

    def get_by_brand_and_slug(self, brand_id: UUID, slug: str) -> ProductData | None:
        try:
            obj = Product.objects.get(brand_id=brand_id, slug=slug)
            return self._to_data(obj)
        except Product.DoesNotExist:
            return None


class DjangoBrandRepository:
    def _to_data(self, obj: Brand) -> BrandData:
        return BrandData(
            id=obj.id,
            slug=obj.slug,
            name=obj.name,
            is_active=obj.is_active,
        )

    def get_by_id(self, id: UUID) -> BrandData | None:
        try:
            obj = Brand.objects.get(id=id)
            return self._to_data(obj)
        except Brand.DoesNotExist:
            return None

    def get_by_slug(self, slug: str) -> BrandData | None:
        try:
            obj = Brand.objects.get(slug=slug)
            return self._to_data(obj)
        except Brand.DoesNotExist:
            return None
