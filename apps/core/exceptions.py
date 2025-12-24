import logging

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler

logger = logging.getLogger("apps.core")


class LicenseServiceException(APIException):
    """Base exception for license service errors."""

    pass


class LicenseNotFoundError(LicenseServiceException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "License not found"
    default_code = "license_not_found"


class LicenseExpiredError(LicenseServiceException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "License has expired"
    default_code = "license_expired"


class LicenseSuspendedError(LicenseServiceException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "License is suspended"
    default_code = "license_suspended"


class LicenseCancelledError(LicenseServiceException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "License has been cancelled"
    default_code = "license_cancelled"


class NoSeatsAvailableError(LicenseServiceException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "No seats available for this license"
    default_code = "no_seats_available"


class AlreadyActivatedError(LicenseServiceException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "License already activated on this instance"
    default_code = "already_activated"


class InvalidStateTransitionError(LicenseServiceException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid license state transition"
    default_code = "invalid_state_transition"


class ProductNotFoundError(LicenseServiceException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Product not found"
    default_code = "product_not_found"


class BrandMismatchError(LicenseServiceException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Brand mismatch - you can only access your own resources"
    default_code = "brand_mismatch"


def custom_exception_handler(exc, context):
    """
    Custom exception handler with logging and structured responses.
    """
    # Get the standard error response
    response = exception_handler(exc, context)

    if response is not None:
        # Add error code to response
        error_code = getattr(exc, "default_code", "error")
        error_message = str(exc.detail) if hasattr(exc, "detail") else str(exc)

        response.data = {
            "error": {
                "code": error_code,
                "message": error_message,
                "status": response.status_code,
            }
        }

        # Log the error
        request = context.get("request")
        logger.warning(
            "API Error: %s - %s",
            error_code,
            error_message,
            extra={
                "error_code": error_code,
                "status": response.status_code,
                "path": request.path if request else None,
            },
        )

    return response
