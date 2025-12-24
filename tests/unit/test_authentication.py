import hashlib

from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory

import pytest

from apps.brands.models import Brand
from apps.core.authentication import BrandApiKeyAuthentication


@pytest.mark.django_db
class TestBrandApiKeyAuthentication:
    def setup_method(self):
        self.auth = BrandApiKeyAuthentication()
        self.factory = APIRequestFactory()

    def test_no_api_key_returns_none(self):
        request = self.factory.get("/")
        result = self.auth.authenticate(request)
        assert result is None

    def test_invalid_format_no_colon(self):
        request = self.factory.get("/", HTTP_X_BRAND_API_KEY="invalid-key-no-colon")
        with pytest.raises(AuthenticationFailed) as exc:
            self.auth.authenticate(request)
        assert "Invalid API key format" in str(exc.value)

    def test_brand_not_found(self):
        request = self.factory.get("/", HTTP_X_BRAND_API_KEY="nonexistent:secret")
        with pytest.raises(AuthenticationFailed) as exc:
            self.auth.authenticate(request)
        assert "Invalid brand" in str(exc.value)

    def test_brand_inactive(self):
        Brand.objects.create(
            name="Inactive",
            slug="inactive",
            api_key_hash=hashlib.sha256(b"secret").hexdigest(),
            is_active=False,
        )
        request = self.factory.get("/", HTTP_X_BRAND_API_KEY="inactive:secret")
        with pytest.raises(AuthenticationFailed) as exc:
            self.auth.authenticate(request)
        assert "Invalid brand" in str(exc.value)

    def test_invalid_secret(self, brand):
        request = self.factory.get("/", HTTP_X_BRAND_API_KEY=f"{brand.slug}:wrong_secret")
        with pytest.raises(AuthenticationFailed) as exc:
            self.auth.authenticate(request)
        assert "Invalid API key" in str(exc.value)

    def test_valid_authentication(self, brand):
        request = self.factory.get("/", HTTP_X_BRAND_API_KEY=f"{brand.slug}:test_secret")
        result = self.auth.authenticate(request)
        assert result is not None
        assert result[0] == brand
        assert result[1] == "brand_api_key"

    def test_hash_key_static_method(self):
        result = BrandApiKeyAuthentication._hash_key("test")
        expected = hashlib.sha256(b"test").hexdigest()
        assert result == expected
