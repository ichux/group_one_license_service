from django.utils import timezone

import pytest

from apps.brands.models import Brand, Product
from apps.licenses.models import Activation, AuditLog, License


@pytest.mark.django_db
class TestLicenseModel:
    """Tests for the License model."""

    def test_is_valid_returns_true_for_valid_license(self, license: License):
        """A valid license with future expiration should return is_valid=True."""
        assert license.is_valid is True

    def test_is_valid_returns_false_for_expired_license(self, expired_license: License):
        """An expired license should return is_valid=False."""
        assert expired_license.is_valid is False

    def test_is_valid_returns_false_for_suspended_license(self, suspended_license: License):
        """A suspended license should return is_valid=False."""
        assert suspended_license.is_valid is False

    def test_is_expired_returns_true_for_expired_license(self, expired_license: License):
        """An expired license should return is_expired=True."""
        assert expired_license.is_expired is True

    def test_is_expired_returns_false_for_valid_license(self, license: License):
        """A non-expired license should return is_expired=False."""
        assert license.is_expired is False

    def test_used_seats_returns_zero_for_no_activations(self, license: License):
        """License with no activations should have 0 used seats."""
        assert license.used_seats == 0

    def test_used_seats_counts_active_activations(self, license: License, activation: Activation):
        """License should count active activations."""
        assert license.used_seats == 1

    def test_remaining_seats_calculated_correctly(self, license: License, activation: Activation):
        """Remaining seats should be max_seats - used_seats."""
        assert license.remaining_seats == 2  # max_seats=3, used=1

    def test_remaining_seats_returns_none_for_unlimited(self, license: License):
        """License with null max_seats should return None for remaining_seats."""
        license.max_seats = None
        license.save()
        assert license.remaining_seats is None

    def test_can_activate_returns_true_when_seats_available(self, license: License):
        """can_activate should return True when seats are available."""
        assert license.can_activate() is True

    def test_can_activate_returns_false_when_no_seats(self, license: License):
        """can_activate should return False when no seats available."""
        license.max_seats = 0
        license.save()
        assert license.can_activate() is False

    def test_can_activate_returns_false_when_invalid(self, suspended_license: License):
        """can_activate should return False for invalid licenses."""
        assert suspended_license.can_activate() is False

    def test_can_activate_returns_true_for_unlimited_seats(self, license: License):
        """can_activate should return True for unlimited seats."""
        license.max_seats = None
        license.save()
        assert license.can_activate() is True


@pytest.mark.django_db
class TestLicenseKeyModel:
    """Tests for the LicenseKey model."""

    def test_str_representation(self, license_key):
        """LicenseKey string representation shows truncated key."""
        str_repr = str(license_key)
        assert "..." in str_repr
        assert len(str_repr) < len(license_key.key)


@pytest.mark.django_db
class TestActivationModel:
    """Tests for the Activation model."""

    def test_str_representation_active(self, activation: Activation):
        """Active activation shows 'Active' in string representation."""
        assert "Active" in str(activation)

    def test_str_representation_inactive(self, activation: Activation):
        """Inactive activation shows 'Inactive' in string representation."""
        activation.is_active = False
        activation.deactivated_at = timezone.now()
        activation.save()
        assert "Inactive" in str(activation)


@pytest.mark.django_db
class TestBrandModel:
    def test_str_representation(self, brand: Brand):
        assert str(brand) == brand.name


@pytest.mark.django_db
class TestProductModel:
    def test_str_representation(self, product: Product):
        assert str(product) == f"{product.brand.slug}/{product.slug}"


@pytest.mark.django_db
class TestLicenseStrRepr:
    def test_str_representation(self, license: License):
        str_repr = str(license)
        assert license.product.slug in str_repr
        assert license.status in str_repr


@pytest.mark.django_db
class TestAuditLogModel:
    def test_str_representation(self, license: License):
        audit_log = AuditLog.objects.create(
            license=license,
            action="license_created",
            actor_type="system",
            actor_id="test",
        )
        str_repr = str(audit_log)
        assert "license_created" in str_repr
