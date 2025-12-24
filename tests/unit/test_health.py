from rest_framework import status

import pytest


@pytest.mark.django_db
class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_check_returns_200(self, api_client):
        """Health check endpoint should return 200 when healthy."""
        response = api_client.get("/health/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "healthy"

    def test_health_check_includes_database_status(self, api_client):
        """Health check should include database status."""
        response = api_client.get("/health/")
        assert "database" in response.json()["checks"]

    def test_liveness_check_returns_200(self, api_client):
        """Liveness probe should return 200."""
        response = api_client.get("/health/live/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["alive"] is True

    def test_readiness_check_returns_200(self, api_client):
        """Readiness probe should return 200."""
        response = api_client.get("/health/ready/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["ready"] is True
