import uuid

import pytest

from apps.licenses.models import LicenseKey, LicenseStatus
from apps.licenses.repositories_django import (
    DjangoActivationRepository,
    DjangoBrandRepository,
    DjangoLicenseKeyRepository,
    DjangoLicenseRepository,
    DjangoProductRepository,
)


@pytest.mark.django_db
class TestDjangoLicenseKeyRepository:
    def setup_method(self):
        self.repo = DjangoLicenseKeyRepository()

    def test_get_by_id_not_found(self):
        result = self.repo.get_by_id(uuid.uuid4())
        assert result is None

    def test_get_by_id_found(self, license_key):
        result = self.repo.get_by_id(license_key.id)
        assert result is not None
        assert result.key == license_key.key

    def test_get_by_brand_and_key_not_found(self, brand):
        result = self.repo.get_by_brand_and_key(brand.id, "NONEXISTENT-KEY")
        assert result is None

    def test_list_by_email_with_brand_filter(self, brand, license_key, another_brand):
        LicenseKey.objects.create(
            brand=another_brand,
            key="OTHER-KEY",
            customer_email=license_key.customer_email,
        )
        results = self.repo.list_by_email(license_key.customer_email, brand_id=brand.id)
        assert len(results) == 1
        assert results[0].key == license_key.key


@pytest.mark.django_db
class TestDjangoLicenseRepository:
    def setup_method(self):
        self.repo = DjangoLicenseRepository()

    def test_get_by_id_not_found(self):
        result = self.repo.get_by_id(uuid.uuid4())
        assert result is None

    def test_get_by_id_found(self, license):
        result = self.repo.get_by_id(license.id)
        assert result is not None
        assert result.id == license.id

    def test_update_status_not_found(self):
        result = self.repo.update_status(uuid.uuid4(), LicenseStatus.SUSPENDED)
        assert result is None

    def test_update_status_success(self, license):
        result = self.repo.update_status(license.id, LicenseStatus.SUSPENDED)
        assert result is not None
        assert result.status == LicenseStatus.SUSPENDED


@pytest.mark.django_db
class TestDjangoActivationRepository:
    def setup_method(self):
        self.repo = DjangoActivationRepository()

    def test_count_active_by_license(self, license, activation):
        count = self.repo.count_active_by_license(license.id)
        assert count == 1

    def test_count_active_by_license_no_activations(self, license):
        count = self.repo.count_active_by_license(license.id)
        assert count == 0

    def test_deactivate_not_found(self):
        result = self.repo.deactivate(uuid.uuid4())
        assert result is None

    def test_deactivate_success(self, activation):
        result = self.repo.deactivate(activation.id)
        assert result is not None
        assert result.is_active is False
        assert result.deactivated_at is not None


@pytest.mark.django_db
class TestDjangoProductRepository:
    def setup_method(self):
        self.repo = DjangoProductRepository()

    def test_get_by_id_not_found(self):
        result = self.repo.get_by_id(uuid.uuid4())
        assert result is None

    def test_get_by_brand_and_slug_not_found(self, brand):
        result = self.repo.get_by_brand_and_slug(brand.id, "nonexistent-slug")
        assert result is None

    def test_get_by_brand_and_slug_found(self, product):
        result = self.repo.get_by_brand_and_slug(product.brand_id, product.slug)
        assert result is not None
        assert result.slug == product.slug


@pytest.mark.django_db
class TestDjangoBrandRepository:
    def setup_method(self):
        self.repo = DjangoBrandRepository()

    def test_get_by_id_not_found(self):
        result = self.repo.get_by_id(uuid.uuid4())
        assert result is None

    def test_get_by_id_found(self, brand):
        result = self.repo.get_by_id(brand.id)
        assert result is not None
        assert result.slug == brand.slug

    def test_get_by_slug_not_found(self):
        result = self.repo.get_by_slug("nonexistent-slug")
        assert result is None

    def test_get_by_slug_found(self, brand):
        result = self.repo.get_by_slug(brand.slug)
        assert result is not None
        assert result.id == brand.id
