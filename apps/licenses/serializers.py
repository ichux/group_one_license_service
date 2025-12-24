from rest_framework import serializers


class ProductLicenseInputSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    expires_at = serializers.DateTimeField()
    max_seats = serializers.IntegerField(required=False, allow_null=True, min_value=1)


class CreateLicenseKeySerializer(serializers.Serializer):
    customer_email = serializers.EmailField()
    external_reference = serializers.CharField(required=False, allow_blank=True)
    license_key = serializers.CharField(required=False, max_length=64)
    products = ProductLicenseInputSerializer(many=True, min_length=1)  # type: ignore[call-arg]


class AddLicenseSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    expires_at = serializers.DateTimeField()
    max_seats = serializers.IntegerField(required=False, allow_null=True, min_value=1)


class LicenseOutputSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    product_slug = serializers.CharField()
    status = serializers.CharField()
    expires_at = serializers.DateTimeField()
    max_seats = serializers.IntegerField(allow_null=True)
    used_seats = serializers.IntegerField()
    created_at = serializers.DateTimeField()


class LicenseKeyOutputSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    key = serializers.CharField()
    brand_slug = serializers.CharField()
    customer_email = serializers.EmailField()
    external_reference = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()
    licenses = LicenseOutputSerializer(many=True)


class ActivateRequestSerializer(serializers.Serializer):
    license_key = serializers.CharField(max_length=64)
    product_slug = serializers.SlugField(max_length=100)
    instance_id = serializers.CharField(max_length=500)
    instance_name = serializers.CharField(required=False, max_length=255, allow_blank=True)


class ActivationOutputSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    instance_id = serializers.CharField()
    instance_name = serializers.CharField()
    is_active = serializers.BooleanField()
    activated_at = serializers.DateTimeField()


class DeactivateRequestSerializer(serializers.Serializer):
    license_key = serializers.CharField(max_length=64)
    product_slug = serializers.SlugField(max_length=100)
    instance_id = serializers.CharField(max_length=500)


class StatusRequestSerializer(serializers.Serializer):
    license_key = serializers.CharField(max_length=64)
    product_slug = serializers.SlugField(max_length=100)
    instance_id = serializers.CharField(required=False, max_length=500)


class StatusOutputSerializer(serializers.Serializer):
    license_key = serializers.CharField()
    customer_email = serializers.EmailField()
    product_slug = serializers.CharField()
    status = serializers.CharField()
    is_valid = serializers.BooleanField()  # type: ignore[assignment]
    expires_at = serializers.DateTimeField()
    max_seats = serializers.IntegerField(allow_null=True)
    used_seats = serializers.IntegerField()
    remaining_seats = serializers.IntegerField(allow_null=True)
    instance_activated = serializers.BooleanField()


class CustomerLicenseOutputSerializer(serializers.Serializer):
    license_key = serializers.CharField()
    brand_slug = serializers.CharField()
    customer_email = serializers.EmailField()
    licenses = LicenseOutputSerializer(many=True)


class EmailQuerySerializer(serializers.Serializer):
    email = serializers.EmailField()
    brand_slug = serializers.CharField(required=False)
