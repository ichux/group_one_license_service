import hashlib
import secrets

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class BrandApiKeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        api_key = request.headers.get("X-Brand-Api-Key")

        if not api_key:
            return None

        try:
            brand_slug, secret = api_key.split(":", 1)
        except ValueError:
            raise AuthenticationFailed("Invalid API key format")

        from apps.brands.models import Brand

        try:
            brand = Brand.objects.get(slug=brand_slug, is_active=True)
        except Brand.DoesNotExist:
            raise AuthenticationFailed("Invalid brand")

        expected_hash = brand.api_key_hash
        provided_hash = self._hash_key(secret)

        if not secrets.compare_digest(expected_hash, provided_hash):
            raise AuthenticationFailed("Invalid API key")

        return (brand, "brand_api_key")

    @staticmethod
    def _hash_key(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()
