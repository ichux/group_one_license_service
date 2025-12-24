import time

from django.db import connection
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from drf_spectacular.utils import extend_schema


@extend_schema(
    tags=["Health"],
    summary="Health check",
    description="Returns the health status of the service and its dependencies.",
)
@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """
    Comprehensive health check endpoint.
    Returns 200 if service is healthy, 503 otherwise.
    """
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "checks": {},
    }

    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status["checks"]["database"] = "ok"
    except Exception as exc:
        health_status["checks"]["database"] = f"error: {str(exc)}"
        health_status["status"] = "unhealthy"

    status_code = 200 if health_status["status"] == "healthy" else 503
    return JsonResponse(health_status, status=status_code)


@extend_schema(
    tags=["Health"],
    summary="Liveness probe",
    description="Kubernetes liveness probe - is the service alive?",
)
@api_view(["GET"])
@permission_classes([AllowAny])
def liveness_check(request):
    """Liveness probe - is the service alive?"""
    return JsonResponse({"alive": True})


@extend_schema(
    tags=["Health"],
    summary="Readiness probe",
    description="Kubernetes readiness probe - is the service ready to accept traffic?",
)
@api_view(["GET"])
@permission_classes([AllowAny])
def readiness_check(request):
    """Readiness probe - is the service ready to accept traffic?"""
    return JsonResponse({"ready": True})
