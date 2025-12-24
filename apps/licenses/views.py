from uuid import UUID as UUIDType

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.licenses.repositories_django import (
    DjangoActivationRepository,
    DjangoBrandRepository,
    DjangoLicenseKeyRepository,
    DjangoLicenseRepository,
    DjangoProductRepository,
)
from apps.licenses.serializers import (
    ActivateRequestSerializer,
    ActivationOutputSerializer,
    AddLicenseSerializer,
    CreateLicenseKeySerializer,
    CustomerLicenseOutputSerializer,
    DeactivateRequestSerializer,
    EmailQuerySerializer,
    LicenseKeyOutputSerializer,
    LicenseOutputSerializer,
    StatusOutputSerializer,
    StatusRequestSerializer,
)
from apps.licenses.services import (
    ConflictError,
    LicenseActivationService,
    LicenseProvisioningService,
    LicenseQueryService,
    LicenseStatusService,
    NotFoundError,
    ValidationError,
)


def get_provisioning_service() -> LicenseProvisioningService:
    return LicenseProvisioningService(
        license_key_repo=DjangoLicenseKeyRepository(),
        license_repo=DjangoLicenseRepository(),
        product_repo=DjangoProductRepository(),
        brand_repo=DjangoBrandRepository(),
    )


def get_activation_service() -> LicenseActivationService:
    return LicenseActivationService(
        license_key_repo=DjangoLicenseKeyRepository(),
        license_repo=DjangoLicenseRepository(),
        activation_repo=DjangoActivationRepository(),
        product_repo=DjangoProductRepository(),
    )


def get_status_service() -> LicenseStatusService:
    return LicenseStatusService(
        license_key_repo=DjangoLicenseKeyRepository(),
        license_repo=DjangoLicenseRepository(),
        activation_repo=DjangoActivationRepository(),
        product_repo=DjangoProductRepository(),
    )


def get_query_service() -> LicenseQueryService:
    return LicenseQueryService(
        license_key_repo=DjangoLicenseKeyRepository(),
        license_repo=DjangoLicenseRepository(),
    )


def handle_service_error(exc: Exception) -> Response:
    if isinstance(exc, NotFoundError):
        return Response(
            {"error": {"code": exc.code, "message": exc.message}},
            status=status.HTTP_404_NOT_FOUND,
        )
    if isinstance(exc, ValidationError):
        return Response(
            {"error": {"code": exc.code, "message": exc.message}},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if isinstance(exc, ConflictError):
        return Response(
            {"error": {"code": exc.code, "message": exc.message}},
            status=status.HTTP_409_CONFLICT,
        )
    raise exc


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_license_key(request: Request, brand_id: UUIDType) -> Response:
    serializer = CreateLicenseKeySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    service = get_provisioning_service()

    try:
        result = service.provision_license_key(
            brand_id=brand_id,
            customer_email=data["customer_email"],
            products=data["products"],
            external_reference=data.get("external_reference"),
            license_key=data.get("license_key"),
        )
    except (NotFoundError, ValidationError, ConflictError) as exc:
        return handle_service_error(exc)

    output = {
        "id": result.license_key.id,
        "key": result.license_key.key,
        "brand_slug": result.license_key.brand_slug,
        "customer_email": result.license_key.customer_email,
        "external_reference": result.license_key.external_reference,
        "created_at": result.license_key.created_at,
        "licenses": [
            {
                "id": lic.id,
                "product_slug": lic.product_slug,
                "status": lic.status,
                "expires_at": lic.expires_at,
                "max_seats": lic.max_seats,
                "used_seats": lic.used_seats,
                "created_at": lic.created_at,
            }
            for lic in result.licenses
        ],
    }
    return Response(LicenseKeyOutputSerializer(output).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_license_key(request: Request, brand_id: UUIDType, key: str) -> Response:
    service = get_provisioning_service()

    try:
        result = service.get_license_key_details(brand_id=brand_id, license_key=key)
    except NotFoundError as exc:
        return handle_service_error(exc)

    output = {
        "id": result.license_key.id,
        "key": result.license_key.key,
        "brand_slug": result.license_key.brand_slug,
        "customer_email": result.license_key.customer_email,
        "external_reference": result.license_key.external_reference,
        "created_at": result.license_key.created_at,
        "licenses": [
            {
                "id": lic.id,
                "product_slug": lic.product_slug,
                "status": lic.status,
                "expires_at": lic.expires_at,
                "max_seats": lic.max_seats,
                "used_seats": lic.used_seats,
                "created_at": lic.created_at,
            }
            for lic in result.licenses
        ],
    }
    return Response(LicenseKeyOutputSerializer(output).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_license(request: Request, brand_id: UUIDType, key: str) -> Response:
    serializer = AddLicenseSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    service = get_provisioning_service()

    try:
        result = service.add_license_to_key(
            brand_id=brand_id,
            license_key=key,
            product_id=data["product_id"],
            expires_at=data["expires_at"],
            max_seats=data.get("max_seats"),
        )
    except (NotFoundError, ValidationError, ConflictError) as exc:
        return handle_service_error(exc)

    output = {
        "id": result.id,
        "product_slug": result.product_slug,
        "status": result.status,
        "expires_at": result.expires_at,
        "max_seats": result.max_seats,
        "used_seats": result.used_seats,
        "created_at": result.created_at,
    }
    return Response(LicenseOutputSerializer(output).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
def activate_license(request: Request) -> Response:
    serializer = ActivateRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    service = get_activation_service()

    ip_address = request.META.get("REMOTE_ADDR")
    user_agent = request.META.get("HTTP_USER_AGENT", "")

    try:
        result = service.activate(
            license_key=data["license_key"],
            product_slug=data["product_slug"],
            instance_id=data["instance_id"],
            instance_name=data.get("instance_name", ""),
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except (NotFoundError, ValidationError) as exc:
        return handle_service_error(exc)

    output = {
        "id": result.id,
        "instance_id": result.instance_id,
        "instance_name": result.instance_name,
        "is_active": result.is_active,
        "activated_at": result.activated_at,
    }
    return Response(ActivationOutputSerializer(output).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
def deactivate_license(request: Request) -> Response:
    serializer = DeactivateRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    service = get_activation_service()

    try:
        result = service.deactivate(
            license_key=data["license_key"],
            product_slug=data["product_slug"],
            instance_id=data["instance_id"],
        )
    except NotFoundError as exc:
        return handle_service_error(exc)

    output = {
        "id": result.id,
        "instance_id": result.instance_id,
        "instance_name": result.instance_name,
        "is_active": result.is_active,
        "activated_at": result.activated_at,
    }
    return Response(ActivationOutputSerializer(output).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def check_status(request: Request) -> Response:
    serializer = StatusRequestSerializer(data=request.query_params)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    service = get_status_service()

    try:
        result = service.get_status(
            license_key=data["license_key"],
            product_slug=data["product_slug"],
            instance_id=data.get("instance_id"),
        )
    except NotFoundError as exc:
        return handle_service_error(exc)

    return Response(StatusOutputSerializer(result).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_by_email(request: Request) -> Response:
    serializer = EmailQuerySerializer(data=request.query_params)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    service = get_query_service()

    brand_id = None
    if data.get("brand_slug"):
        brand_repo = DjangoBrandRepository()
        brand = brand_repo.get_by_slug(data["brand_slug"])
        if brand:
            brand_id = brand.id

    results = service.list_by_customer_email(email=data["email"], brand_id=brand_id)

    output = [
        {
            "license_key": r.license_key,
            "brand_slug": r.brand_slug,
            "customer_email": r.customer_email,
            "licenses": [
                {
                    "id": lic.id,
                    "product_slug": lic.product_slug,
                    "status": lic.status,
                    "expires_at": lic.expires_at,
                    "max_seats": lic.max_seats,
                    "used_seats": lic.used_seats,
                    "created_at": lic.created_at,
                }
                for lic in r.licenses
            ],
        }
        for r in results
    ]
    return Response(CustomerLicenseOutputSerializer(output, many=True).data)
