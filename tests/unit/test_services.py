from datetime import timedelta
from unittest.mock import Mock
from uuid import uuid4

from django.utils import timezone

import pytest

from apps.licenses.repositories import (
    ActivationData,
    BrandData,
    LicenseData,
    LicenseKeyData,
    ProductData,
)
from apps.licenses.services import (
    ConflictError,
    LicenseActivationService,
    LicenseProvisioningService,
    LicenseQueryService,
    LicenseStatusService,
    NotFoundError,
    ValidationError,
    generate_license_key,
)


class TestGenerateLicenseKey:
    def test_generates_32_char_key_without_prefix(self):
        key = generate_license_key()
        assert len(key) == 35  # 32 chars + 3 dashes
        assert key.count("-") == 3

    def test_generates_key_with_prefix(self):
        key = generate_license_key("WPR")
        assert key.startswith("WPR-")
        assert len(key) == 39  # WPR- + 32 chars + 3 dashes


class TestLicenseProvisioningService:
    @pytest.fixture
    def mock_repos(self):
        return {
            "license_key_repo": Mock(),
            "license_repo": Mock(),
            "product_repo": Mock(),
            "brand_repo": Mock(),
        }

    @pytest.fixture
    def service(self, mock_repos):
        return LicenseProvisioningService(**mock_repos)

    @pytest.fixture
    def brand_data(self):
        return BrandData(
            id=uuid4(),
            slug="wp-rocket",
            name="WP Rocket",
            is_active=True,
        )

    @pytest.fixture
    def product_data(self, brand_data):
        return ProductData(
            id=uuid4(),
            slug="plugin",
            name="WP Rocket Plugin",
            brand_id=brand_data.id,
            default_max_seats=3,
            is_active=True,
        )

    def test_provision_license_key_success(self, service, mock_repos, brand_data, product_data):
        mock_repos["brand_repo"].get_by_id.return_value = brand_data
        mock_repos["product_repo"].get_by_id.return_value = product_data
        mock_repos["license_key_repo"].get_by_key.return_value = None

        license_key_data = LicenseKeyData(
            id=uuid4(),
            key="TEST-KEY",
            brand_id=brand_data.id,
            brand_slug=brand_data.slug,
            customer_email="test@example.com",
            external_reference=None,
            created_at=timezone.now(),
        )
        mock_repos["license_key_repo"].create.return_value = license_key_data

        license_data = LicenseData(
            id=uuid4(),
            license_key_id=license_key_data.id,
            license_key="TEST-KEY",
            product_id=product_data.id,
            product_slug=product_data.slug,
            status="valid",
            expires_at=timezone.now() + timedelta(days=365),
            max_seats=3,
            used_seats=0,
            created_at=timezone.now(),
        )
        mock_repos["license_repo"].create.return_value = license_data

        result = service.provision_license_key(
            brand_id=brand_data.id,
            customer_email="test@example.com",
            products=[
                {"product_id": product_data.id, "expires_at": timezone.now() + timedelta(days=365)}
            ],
        )

        assert result.license_key.customer_email == "test@example.com"
        assert len(result.licenses) == 1

    def test_provision_license_key_brand_not_found(self, service, mock_repos):
        mock_repos["brand_repo"].get_by_id.return_value = None

        with pytest.raises(NotFoundError) as exc:
            service.provision_license_key(
                brand_id=uuid4(),
                customer_email="test@example.com",
                products=[{"product_id": uuid4(), "expires_at": timezone.now()}],
            )
        assert exc.value.code == "brand_not_found"

    def test_provision_license_key_brand_inactive(self, service, mock_repos, brand_data):
        brand_data.is_active = False
        mock_repos["brand_repo"].get_by_id.return_value = brand_data

        with pytest.raises(ValidationError) as exc:
            service.provision_license_key(
                brand_id=brand_data.id,
                customer_email="test@example.com",
                products=[{"product_id": uuid4(), "expires_at": timezone.now()}],
            )
        assert exc.value.code == "brand_inactive"

    def test_provision_license_key_no_products(self, service, mock_repos, brand_data):
        mock_repos["brand_repo"].get_by_id.return_value = brand_data

        with pytest.raises(ValidationError) as exc:
            service.provision_license_key(
                brand_id=brand_data.id,
                customer_email="test@example.com",
                products=[],
            )
        assert exc.value.code == "no_products"

    def test_provision_license_key_product_not_found(self, service, mock_repos, brand_data):
        mock_repos["brand_repo"].get_by_id.return_value = brand_data
        mock_repos["product_repo"].get_by_id.return_value = None

        with pytest.raises(NotFoundError) as exc:
            service.provision_license_key(
                brand_id=brand_data.id,
                customer_email="test@example.com",
                products=[{"product_id": uuid4(), "expires_at": timezone.now()}],
            )
        assert exc.value.code == "product_not_found"

    def test_provision_license_key_duplicate_key(
        self, service, mock_repos, brand_data, product_data
    ):
        mock_repos["brand_repo"].get_by_id.return_value = brand_data
        mock_repos["product_repo"].get_by_id.return_value = product_data
        mock_repos["license_key_repo"].get_by_key.return_value = LicenseKeyData(
            id=uuid4(),
            key="EXISTING",
            brand_id=brand_data.id,
            brand_slug=brand_data.slug,
            customer_email="other@example.com",
            external_reference=None,
            created_at=timezone.now(),
        )

        with pytest.raises(ConflictError) as exc:
            service.provision_license_key(
                brand_id=brand_data.id,
                customer_email="test@example.com",
                products=[{"product_id": product_data.id, "expires_at": timezone.now()}],
                license_key="EXISTING",
            )
        assert exc.value.code == "key_exists"


class TestLicenseActivationService:
    @pytest.fixture
    def mock_repos(self):
        return {
            "license_key_repo": Mock(),
            "license_repo": Mock(),
            "activation_repo": Mock(),
            "product_repo": Mock(),
        }

    @pytest.fixture
    def service(self, mock_repos):
        return LicenseActivationService(**mock_repos)

    @pytest.fixture
    def license_key_data(self):
        return LicenseKeyData(
            id=uuid4(),
            key="TEST-KEY",
            brand_id=uuid4(),
            brand_slug="wp-rocket",
            customer_email="test@example.com",
            external_reference=None,
            created_at=timezone.now(),
        )

    @pytest.fixture
    def product_data(self, license_key_data):
        return ProductData(
            id=uuid4(),
            slug="plugin",
            name="WP Rocket Plugin",
            brand_id=license_key_data.brand_id,
            default_max_seats=3,
            is_active=True,
        )

    @pytest.fixture
    def license_data(self, license_key_data, product_data):
        return LicenseData(
            id=uuid4(),
            license_key_id=license_key_data.id,
            license_key=license_key_data.key,
            product_id=product_data.id,
            product_slug=product_data.slug,
            status="valid",
            expires_at=timezone.now() + timedelta(days=365),
            max_seats=3,
            used_seats=0,
            created_at=timezone.now(),
        )

    def test_activate_success(
        self, service, mock_repos, license_key_data, product_data, license_data
    ):
        mock_repos["license_key_repo"].get_by_key.return_value = license_key_data
        mock_repos["product_repo"].get_by_brand_and_slug.return_value = product_data
        mock_repos["license_repo"].get_by_key_and_product.return_value = license_data
        mock_repos["activation_repo"].get_active_by_license_and_instance.return_value = None

        activation_data = ActivationData(
            id=uuid4(),
            license_id=license_data.id,
            instance_id="https://example.com",
            instance_name="Example Site",
            is_active=True,
            activated_at=timezone.now(),
            deactivated_at=None,
            ip_address="192.168.1.1",
        )
        mock_repos["activation_repo"].create.return_value = activation_data

        result = service.activate(
            license_key="TEST-KEY",
            product_slug="plugin",
            instance_id="https://example.com",
            instance_name="Example Site",
            ip_address="192.168.1.1",
            now=timezone.now(),
        )

        assert result.instance_id == "https://example.com"
        assert result.is_active is True

    def test_activate_returns_existing_activation(
        self, service, mock_repos, license_key_data, product_data, license_data
    ):
        mock_repos["license_key_repo"].get_by_key.return_value = license_key_data
        mock_repos["product_repo"].get_by_brand_and_slug.return_value = product_data
        mock_repos["license_repo"].get_by_key_and_product.return_value = license_data

        existing = ActivationData(
            id=uuid4(),
            license_id=license_data.id,
            instance_id="https://example.com",
            instance_name="Example Site",
            is_active=True,
            activated_at=timezone.now(),
            deactivated_at=None,
            ip_address="192.168.1.1",
        )
        mock_repos["activation_repo"].get_active_by_license_and_instance.return_value = existing

        result = service.activate(
            license_key="TEST-KEY",
            product_slug="plugin",
            instance_id="https://example.com",
            now=timezone.now(),
        )

        assert result.id == existing.id
        mock_repos["activation_repo"].create.assert_not_called()

    def test_activate_key_not_found(self, service, mock_repos):
        mock_repos["license_key_repo"].get_by_key.return_value = None

        with pytest.raises(NotFoundError) as exc:
            service.activate(
                license_key="INVALID",
                product_slug="plugin",
                instance_id="https://example.com",
            )
        assert exc.value.code == "key_not_found"

    def test_activate_no_seats_available(
        self, service, mock_repos, license_key_data, product_data, license_data
    ):
        license_data.used_seats = 3  # Max seats reached
        mock_repos["license_key_repo"].get_by_key.return_value = license_key_data
        mock_repos["product_repo"].get_by_brand_and_slug.return_value = product_data
        mock_repos["license_repo"].get_by_key_and_product.return_value = license_data
        mock_repos["activation_repo"].get_active_by_license_and_instance.return_value = None

        with pytest.raises(ValidationError) as exc:
            service.activate(
                license_key="TEST-KEY",
                product_slug="plugin",
                instance_id="https://example.com",
                now=timezone.now(),
            )
        assert exc.value.code == "no_seats_available"

    def test_activate_license_expired(
        self, service, mock_repos, license_key_data, product_data, license_data
    ):
        license_data.expires_at = timezone.now() - timedelta(days=1)
        mock_repos["license_key_repo"].get_by_key.return_value = license_key_data
        mock_repos["product_repo"].get_by_brand_and_slug.return_value = product_data
        mock_repos["license_repo"].get_by_key_and_product.return_value = license_data

        with pytest.raises(ValidationError) as exc:
            service.activate(
                license_key="TEST-KEY",
                product_slug="plugin",
                instance_id="https://example.com",
                now=timezone.now(),
            )
        assert exc.value.code == "license_invalid"


class TestLicenseStatusService:
    @pytest.fixture
    def mock_repos(self):
        return {
            "license_key_repo": Mock(),
            "license_repo": Mock(),
            "activation_repo": Mock(),
            "product_repo": Mock(),
        }

    @pytest.fixture
    def service(self, mock_repos):
        return LicenseStatusService(**mock_repos)

    def test_get_status_success(self, service, mock_repos):
        brand_id = uuid4()
        license_key_data = LicenseKeyData(
            id=uuid4(),
            key="TEST-KEY",
            brand_id=brand_id,
            brand_slug="wp-rocket",
            customer_email="test@example.com",
            external_reference=None,
            created_at=timezone.now(),
        )
        product_data = ProductData(
            id=uuid4(),
            slug="plugin",
            name="WP Rocket Plugin",
            brand_id=brand_id,
            default_max_seats=3,
            is_active=True,
        )
        license_data = LicenseData(
            id=uuid4(),
            license_key_id=license_key_data.id,
            license_key=license_key_data.key,
            product_id=product_data.id,
            product_slug=product_data.slug,
            status="valid",
            expires_at=timezone.now() + timedelta(days=365),
            max_seats=3,
            used_seats=1,
            created_at=timezone.now(),
        )

        mock_repos["license_key_repo"].get_by_key.return_value = license_key_data
        mock_repos["product_repo"].get_by_brand_and_slug.return_value = product_data
        mock_repos["license_repo"].get_by_key_and_product.return_value = license_data
        mock_repos["activation_repo"].get_active_by_license_and_instance.return_value = None

        result = service.get_status(
            license_key="TEST-KEY",
            product_slug="plugin",
            instance_id="https://example.com",
        )

        assert result.is_valid is True
        assert result.status == "valid"
        assert result.used_seats == 1
        assert result.remaining_seats == 2
        assert result.instance_activated is False

    def test_get_status_with_active_instance(self, service, mock_repos):
        brand_id = uuid4()
        license_id = uuid4()
        license_key_data = LicenseKeyData(
            id=uuid4(),
            key="TEST-KEY",
            brand_id=brand_id,
            brand_slug="wp-rocket",
            customer_email="test@example.com",
            external_reference=None,
            created_at=timezone.now(),
        )
        product_data = ProductData(
            id=uuid4(),
            slug="plugin",
            name="WP Rocket Plugin",
            brand_id=brand_id,
            default_max_seats=3,
            is_active=True,
        )
        license_data = LicenseData(
            id=license_id,
            license_key_id=license_key_data.id,
            license_key=license_key_data.key,
            product_id=product_data.id,
            product_slug=product_data.slug,
            status="valid",
            expires_at=timezone.now() + timedelta(days=365),
            max_seats=3,
            used_seats=1,
            created_at=timezone.now(),
        )
        activation_data = ActivationData(
            id=uuid4(),
            license_id=license_id,
            instance_id="https://example.com",
            instance_name="Example Site",
            is_active=True,
            activated_at=timezone.now(),
            deactivated_at=None,
            ip_address="192.168.1.1",
        )

        mock_repos["license_key_repo"].get_by_key.return_value = license_key_data
        mock_repos["product_repo"].get_by_brand_and_slug.return_value = product_data
        mock_repos["license_repo"].get_by_key_and_product.return_value = license_data
        mock_repos["activation_repo"].get_active_by_license_and_instance.return_value = (
            activation_data
        )

        result = service.get_status(
            license_key="TEST-KEY",
            product_slug="plugin",
            instance_id="https://example.com",
        )

        assert result.instance_activated is True


class TestLicenseQueryService:
    @pytest.fixture
    def mock_repos(self):
        return {
            "license_key_repo": Mock(),
            "license_repo": Mock(),
        }

    @pytest.fixture
    def service(self, mock_repos):
        return LicenseQueryService(**mock_repos)

    def test_list_by_customer_email(self, service, mock_repos):
        brand_id = uuid4()
        license_key_data = LicenseKeyData(
            id=uuid4(),
            key="TEST-KEY",
            brand_id=brand_id,
            brand_slug="wp-rocket",
            customer_email="test@example.com",
            external_reference=None,
            created_at=timezone.now(),
        )
        license_data = LicenseData(
            id=uuid4(),
            license_key_id=license_key_data.id,
            license_key=license_key_data.key,
            product_id=uuid4(),
            product_slug="plugin",
            status="valid",
            expires_at=timezone.now() + timedelta(days=365),
            max_seats=3,
            used_seats=0,
            created_at=timezone.now(),
        )

        mock_repos["license_key_repo"].list_by_email.return_value = [license_key_data]
        mock_repos["license_repo"].list_by_license_key.return_value = [license_data]

        results = service.list_by_customer_email("test@example.com")

        assert len(results) == 1
        assert results[0].license_key == "TEST-KEY"
        assert results[0].brand_slug == "wp-rocket"
        assert len(results[0].licenses) == 1

    def test_list_by_customer_email_empty(self, service, mock_repos):
        mock_repos["license_key_repo"].list_by_email.return_value = []

        results = service.list_by_customer_email("nonexistent@example.com")

        assert len(results) == 0
