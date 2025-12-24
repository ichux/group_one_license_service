from datetime import timedelta

from django.utils import timezone
from rest_framework import status

import pytest


@pytest.mark.django_db
class TestLicenseKeyProvisioningAPI:
    def test_create_license_key_success(self, api_client, brand, product):
        api_client.credentials(HTTP_X_BRAND_API_KEY=f"{brand.slug}:test_secret")

        response = api_client.post(
            f"/api/v1/brands/{brand.id}/license-keys/",
            {
                "customer_email": "customer@example.com",
                "products": [
                    {
                        "product_id": str(product.id),
                        "expires_at": (timezone.now() + timedelta(days=365)).isoformat(),
                    }
                ],
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["customer_email"] == "customer@example.com"
        assert data["brand_slug"] == brand.slug
        assert len(data["licenses"]) == 1
        assert data["licenses"][0]["product_slug"] == product.slug

    def test_create_license_key_unauthenticated(self, api_client, brand, product):
        response = api_client.post(
            f"/api/v1/brands/{brand.id}/license-keys/",
            {
                "customer_email": "customer@example.com",
                "products": [
                    {
                        "product_id": str(product.id),
                        "expires_at": (timezone.now() + timedelta(days=365)).isoformat(),
                    }
                ],
            },
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_license_key_invalid_product(self, api_client, brand):
        api_client.credentials(HTTP_X_BRAND_API_KEY=f"{brand.slug}:test_secret")
        fake_product_id = "00000000-0000-0000-0000-000000000000"

        response = api_client.post(
            f"/api/v1/brands/{brand.id}/license-keys/",
            {
                "customer_email": "customer@example.com",
                "products": [
                    {
                        "product_id": fake_product_id,
                        "expires_at": (timezone.now() + timedelta(days=365)).isoformat(),
                    }
                ],
            },
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_license_key_details(self, api_client, brand, license_key, license):
        api_client.credentials(HTTP_X_BRAND_API_KEY=f"{brand.slug}:test_secret")

        response = api_client.get(
            f"/api/v1/brands/{brand.id}/license-keys/{license_key.key}/",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["key"] == license_key.key
        assert len(data["licenses"]) >= 1

    def test_add_license_to_existing_key(self, api_client, brand, license_key):
        from apps.brands.models import Product

        new_product = Product.objects.create(
            brand=brand,
            name="Second Product",
            slug="second-product",
        )

        api_client.credentials(HTTP_X_BRAND_API_KEY=f"{brand.slug}:test_secret")

        response = api_client.post(
            f"/api/v1/brands/{brand.id}/license-keys/{license_key.key}/licenses/",
            {
                "product_id": str(new_product.id),
                "expires_at": (timezone.now() + timedelta(days=365)).isoformat(),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["product_slug"] == "second-product"


@pytest.mark.django_db
class TestLicenseActivationAPI:
    def test_activate_license_success(self, api_client, license_key, license):
        response = api_client.post(
            "/api/v1/licenses/activate/",
            {
                "license_key": license_key.key,
                "product_slug": license.product.slug,
                "instance_id": "https://mysite.example.com",
                "instance_name": "My Site",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["instance_id"] == "https://mysite.example.com"
        assert data["is_active"] is True

    def test_activate_license_invalid_key(self, api_client):
        response = api_client.post(
            "/api/v1/licenses/activate/",
            {
                "license_key": "INVALID-KEY",
                "product_slug": "some-product",
                "instance_id": "https://mysite.example.com",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_activate_same_instance_returns_existing(
        self, api_client, license_key, license, activation
    ):
        response = api_client.post(
            "/api/v1/licenses/activate/",
            {
                "license_key": license_key.key,
                "product_slug": license.product.slug,
                "instance_id": activation.instance_id,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert str(data["id"]) == str(activation.id)

    def test_activate_no_seats_available(self, api_client, license_key, license, activation):
        license.max_seats = 1
        license.save()

        response = api_client.post(
            "/api/v1/licenses/activate/",
            {
                "license_key": license_key.key,
                "product_slug": license.product.slug,
                "instance_id": "https://new-site.example.com",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error"]["code"] == "no_seats_available"


@pytest.mark.django_db
class TestLicenseDeactivationAPI:
    def test_deactivate_success(self, api_client, license_key, license, activation):
        response = api_client.post(
            "/api/v1/licenses/deactivate/",
            {
                "license_key": license_key.key,
                "product_slug": license.product.slug,
                "instance_id": activation.instance_id,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_active"] is False

    def test_deactivate_not_found(self, api_client, license_key, license):
        response = api_client.post(
            "/api/v1/licenses/deactivate/",
            {
                "license_key": license_key.key,
                "product_slug": license.product.slug,
                "instance_id": "https://nonexistent.example.com",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestLicenseStatusAPI:
    def test_check_status_success(self, api_client, license_key, license):
        response = api_client.get(
            "/api/v1/licenses/status/",
            {
                "license_key": license_key.key,
                "product_slug": license.product.slug,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_valid"] is True
        assert data["status"] == "valid"

    def test_check_status_with_instance(self, api_client, license_key, license, activation):
        response = api_client.get(
            "/api/v1/licenses/status/",
            {
                "license_key": license_key.key,
                "product_slug": license.product.slug,
                "instance_id": activation.instance_id,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["instance_activated"] is True

    def test_check_status_invalid_key(self, api_client):
        response = api_client.get(
            "/api/v1/licenses/status/",
            {
                "license_key": "INVALID-KEY",
                "product_slug": "some-product",
            },
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestCrossBrandEmailQueryAPI:
    def test_list_by_email_success(self, api_client, brand, license_key):
        api_client.credentials(HTTP_X_BRAND_API_KEY=f"{brand.slug}:test_secret")

        response = api_client.get(
            "/api/v1/licenses/by-email/",
            {"email": license_key.customer_email},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 1
        assert data[0]["customer_email"] == license_key.customer_email

    def test_list_by_email_empty(self, api_client, brand):
        api_client.credentials(HTTP_X_BRAND_API_KEY=f"{brand.slug}:test_secret")

        response = api_client.get(
            "/api/v1/licenses/by-email/",
            {"email": "nonexistent@example.com"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_list_by_email_unauthenticated(self, api_client, license_key):
        response = api_client.get(
            "/api/v1/licenses/by-email/",
            {"email": license_key.customer_email},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_by_email_with_brand_filter(self, api_client, brand, license_key):
        api_client.credentials(HTTP_X_BRAND_API_KEY=f"{brand.slug}:test_secret")

        response = api_client.get(
            "/api/v1/licenses/by-email/",
            {"email": license_key.customer_email, "brand_slug": brand.slug},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 1
        assert all(item["brand_slug"] == brand.slug for item in data)

    def test_list_by_email_with_nonexistent_brand_filter(self, api_client, brand, license_key):
        api_client.credentials(HTTP_X_BRAND_API_KEY=f"{brand.slug}:test_secret")

        response = api_client.get(
            "/api/v1/licenses/by-email/",
            {"email": license_key.customer_email, "brand_slug": "nonexistent-brand"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 1


@pytest.mark.django_db
class TestEdgeCases:
    def test_create_license_key_product_from_different_brand(
        self, api_client, brand, another_brand
    ):
        from apps.brands.models import Product

        other_product = Product.objects.create(
            brand=another_brand,
            name="Other Product",
            slug="other-product",
        )
        api_client.credentials(HTTP_X_BRAND_API_KEY=f"{brand.slug}:test_secret")

        response = api_client.post(
            f"/api/v1/brands/{brand.id}/license-keys/",
            {
                "customer_email": "customer@example.com",
                "products": [
                    {
                        "product_id": str(other_product.id),
                        "expires_at": (timezone.now() + timedelta(days=365)).isoformat(),
                    }
                ],
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error"]["code"] == "product_brand_mismatch"

    def test_create_license_key_inactive_product(self, api_client, brand):
        from apps.brands.models import Product

        inactive_product = Product.objects.create(
            brand=brand,
            name="Inactive Product",
            slug="inactive-product",
            is_active=False,
        )
        api_client.credentials(HTTP_X_BRAND_API_KEY=f"{brand.slug}:test_secret")

        response = api_client.post(
            f"/api/v1/brands/{brand.id}/license-keys/",
            {
                "customer_email": "customer@example.com",
                "products": [
                    {
                        "product_id": str(inactive_product.id),
                        "expires_at": (timezone.now() + timedelta(days=365)).isoformat(),
                    }
                ],
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error"]["code"] == "product_inactive"

    def test_create_license_key_invalid_serializer(self, api_client, brand):
        api_client.credentials(HTTP_X_BRAND_API_KEY=f"{brand.slug}:test_secret")

        response = api_client.post(
            f"/api/v1/brands/{brand.id}/license-keys/",
            {"customer_email": "not-an-email"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_license_key_not_found(self, api_client, brand):
        api_client.credentials(HTTP_X_BRAND_API_KEY=f"{brand.slug}:test_secret")

        response = api_client.get(
            f"/api/v1/brands/{brand.id}/license-keys/NONEXISTENT-KEY/",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_add_license_key_not_found(self, api_client, brand, product):
        api_client.credentials(HTTP_X_BRAND_API_KEY=f"{brand.slug}:test_secret")

        response = api_client.post(
            f"/api/v1/brands/{brand.id}/license-keys/NONEXISTENT-KEY/licenses/",
            {
                "product_id": str(product.id),
                "expires_at": (timezone.now() + timedelta(days=365)).isoformat(),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_add_license_duplicate_product(self, api_client, brand, license_key, license):
        api_client.credentials(HTTP_X_BRAND_API_KEY=f"{brand.slug}:test_secret")

        response = api_client.post(
            f"/api/v1/brands/{brand.id}/license-keys/{license_key.key}/licenses/",
            {
                "product_id": str(license.product.id),
                "expires_at": (timezone.now() + timedelta(days=365)).isoformat(),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["error"]["code"] == "license_exists"

    def test_add_license_invalid_serializer(self, api_client, brand, license_key):
        api_client.credentials(HTTP_X_BRAND_API_KEY=f"{brand.slug}:test_secret")

        response = api_client.post(
            f"/api/v1/brands/{brand.id}/license-keys/{license_key.key}/licenses/",
            {"product_id": "not-a-uuid"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_activate_expired_license(self, api_client, license_key, expired_license):
        response = api_client.post(
            "/api/v1/licenses/activate/",
            {
                "license_key": license_key.key,
                "product_slug": expired_license.product.slug,
                "instance_id": "https://mysite.example.com",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error"]["code"] == "license_invalid"

    def test_activate_invalid_product_slug(self, api_client, license_key):
        response = api_client.post(
            "/api/v1/licenses/activate/",
            {
                "license_key": license_key.key,
                "product_slug": "nonexistent-product",
                "instance_id": "https://mysite.example.com",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_activate_invalid_serializer(self, api_client):
        response = api_client.post(
            "/api/v1/licenses/activate/",
            {"license_key": ""},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_deactivate_invalid_key(self, api_client):
        response = api_client.post(
            "/api/v1/licenses/deactivate/",
            {
                "license_key": "INVALID-KEY",
                "product_slug": "some-product",
                "instance_id": "https://mysite.example.com",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_deactivate_invalid_product(self, api_client, license_key):
        response = api_client.post(
            "/api/v1/licenses/deactivate/",
            {
                "license_key": license_key.key,
                "product_slug": "nonexistent-product",
                "instance_id": "https://mysite.example.com",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_deactivate_invalid_serializer(self, api_client):
        response = api_client.post(
            "/api/v1/licenses/deactivate/",
            {"license_key": ""},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_status_invalid_product(self, api_client, license_key):
        response = api_client.get(
            "/api/v1/licenses/status/",
            {
                "license_key": license_key.key,
                "product_slug": "nonexistent-product",
            },
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_status_invalid_serializer(self, api_client):
        response = api_client.get(
            "/api/v1/licenses/status/",
            {},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_by_email_invalid_serializer(self, api_client, brand):
        api_client.credentials(HTTP_X_BRAND_API_KEY=f"{brand.slug}:test_secret")

        response = api_client.get(
            "/api/v1/licenses/by-email/",
            {"email": "not-an-email"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
