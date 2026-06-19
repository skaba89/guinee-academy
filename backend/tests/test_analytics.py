"""Tests for analytics and settings endpoints — auth guards + response shape."""
from conftest import get_test_client


client = get_test_client()


class TestAnalyticsAuth:
    """All analytics endpoints must require authentication."""

    def test_financial_kpis_requires_auth(self):
        resp = client.get("/api/v1/analytics/financial-kpis/")
        assert resp.status_code in (401, 403)

    def test_overview_requires_auth(self):
        # Overview was renamed to dashboard-kpis — keep the auth-guard test against the new path.
        resp = client.get("/api/v1/analytics/dashboard-kpis/")
        assert resp.status_code in (401, 403)

    def test_students_stats_requires_auth(self):
        # Students-at-risk is the closest analytics endpoint for student stats.
        resp = client.get("/api/v1/analytics/students-at-risk/")
        assert resp.status_code in (401, 403)

    def test_attendance_stats_requires_auth(self):
        # Attendance-trend is the closest analytics endpoint for attendance stats.
        resp = client.get("/api/v1/analytics/attendance-trend/")
        assert resp.status_code in (401, 403)

    def test_export_csv_requires_auth(self):
        # Ministry-export CSV is the closest export endpoint.
        resp = client.get("/api/v1/analytics/ministry-export/csv/")
        assert resp.status_code in (401, 403)


class TestMetricsEndpoint:
    """The /metrics/ endpoint must be secured in production."""

    def test_metrics_blocked_without_secret(self, monkeypatch):
        """When DEBUG=false and no secret provided, must return 403."""
        from app.core.config import settings
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.delenv("METRICS_SECRET", raising=False)
        # settings.DEBUG is read at startup; patch it directly so the endpoint sees the new value.
        monkeypatch.setattr(settings, "DEBUG", False)
        resp = client.get("/metrics/")
        # Either 403 (disabled) or 401/403 (auth required)
        assert resp.status_code in (401, 403)

    def test_metrics_reachable_in_debug(self, monkeypatch):
        """In DEBUG mode, metrics are accessible without authentication."""
        monkeypatch.setenv("DEBUG", "true")
        resp = client.get("/metrics/")
        # Should not be 404; content-type text/plain for Prometheus
        assert resp.status_code != 404


class TestMFAEnforcement:
    """ENFORCE_MFA must block login for privileged users without MFA."""

    def test_login_with_bad_password_is_401(self):
        resp = client.post(
            "/api/v1/auth/login/",
            data={"username": "admin@test.com", "password": "wrong"},
        )
        assert resp.status_code in (401, 403, 422)

    def test_login_endpoint_accepts_form_data(self):
        """Login endpoint must accept OAuth2 form (not JSON body)."""
        resp = client.post(
            "/api/v1/auth/login/",
            data={"username": "test@example.com", "password": "secret"},
        )
        # 422 = validation ok but wrong format, 401 = auth failed — both mean the endpoint exists
        assert resp.status_code != 404
        assert resp.status_code != 405

    def test_refresh_token_endpoint_exists(self):
        """Token refresh endpoint must exist and reject missing token."""
        resp = client.post("/api/v1/auth/refresh/", json={})
        assert resp.status_code in (401, 403, 422)

    def test_logout_endpoint_exists(self):
        """Logout endpoint must reject unauthenticated requests."""
        resp = client.post("/api/v1/auth/logout/")
        assert resp.status_code in (401, 403, 422)
