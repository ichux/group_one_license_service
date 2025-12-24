import hashlib
import uuid

from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.brands.models import Brand, Product
from apps.licenses.models import Activation, License, LicenseKey, LicenseStatus


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def brand(db) -> Brand:
    return Brand.objects.create(
        name="Test Brand",
        slug="test-brand",
        api_key_hash=hashlib.sha256(b"test_secret").hexdigest(),
        is_active=True,
    )


@pytest.fixture
def another_brand(db) -> Brand:
    return Brand.objects.create(
        name="Another Brand",
        slug="another-brand",
        api_key_hash=hashlib.sha256(b"another_secret").hexdigest(),
        is_active=True,
    )


@pytest.fixture
def product(brand: Brand) -> Product:
    return Product.objects.create(
        brand=brand,
        name="Test Product",
        slug="test-product",
        description="A test product",
        is_active=True,
        default_max_seats=3,
    )


@pytest.fixture
def another_product(brand: Brand) -> Product:
    return Product.objects.create(
        brand=brand,
        name="Another Product",
        slug="another-product",
        description="Another test product",
        is_active=True,
        default_max_seats=None,
    )


@pytest.fixture
def license_key(brand: Brand) -> LicenseKey:
    return LicenseKey.objects.create(
        brand=brand,
        key=f"TEST-{uuid.uuid4().hex[:16].upper()}",
        customer_email="test@example.com",
        external_reference="test_ref_123",
    )


@pytest.fixture
def license(license_key: LicenseKey, product: Product) -> License:
    return License.objects.create(
        license_key=license_key,
        product=product,
        status=LicenseStatus.VALID,
        expires_at=timezone.now() + timezone.timedelta(days=365),
        max_seats=3,
    )


@pytest.fixture
def expired_license(license_key: LicenseKey, product: Product) -> License:
    return License.objects.create(
        license_key=license_key,
        product=product,
        status=LicenseStatus.VALID,
        expires_at=timezone.now() - timezone.timedelta(days=1),
        max_seats=3,
    )


@pytest.fixture
def suspended_license(license_key: LicenseKey, product: Product) -> License:
    return License.objects.create(
        license_key=license_key,
        product=product,
        status=LicenseStatus.SUSPENDED,
        expires_at=timezone.now() + timezone.timedelta(days=365),
        max_seats=3,
    )


@pytest.fixture
def activation(license: License) -> Activation:
    return Activation.objects.create(
        license=license,
        instance_id="https://test-site.com",
        instance_name="Test Site",
        is_active=True,
        ip_address="127.0.0.1",
    )


@pytest.fixture
def authenticated_client(api_client: APIClient, brand: Brand) -> APIClient:
    api_client.credentials(HTTP_X_BRAND_API_KEY="test-brand:test_secret")
    return api_client
