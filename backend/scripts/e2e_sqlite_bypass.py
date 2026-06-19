#!/usr/bin/env python3
"""
End-to-end SQLite compatibility test using FastAPI TestClient with auth bypass.

Bypasses JWT auth via dependency_overrides so we can test the actual SQL code paths
without spinning up real authentication state.

Uses a throwaway `e2e_test.db` DB so CI runs are isolated from dev DB.
The harness:
  1. Creates schema from SQLAlchemy metadata
  2. Runs init_db.py seed against the throwaway DB
  3. Exercises 40+ endpoints looking for PostgreSQL-only SQL leaks
  4. Exits 0 on success, non-zero on any SQL_LEAK / SQL_ERROR / SERVER_ERROR
"""
import os
import sys
import uuid
import json
import sqlite3
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timezone

# Backend configuration
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent  # backend/
sys.path.insert(0, str(BACKEND_DIR))

# Use throwaway DB so CI doesn't pollute dev DB
E2E_DB_PATH = BACKEND_DIR / "e2e_test.db"
if E2E_DB_PATH.exists():
    E2E_DB_PATH.unlink()

os.environ["DEBUG"] = "True"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only-32chars"
os.environ["DATABASE_URL"] = f"sqlite:///{E2E_DB_PATH}"
os.environ["DATABASE_URL_SYNC"] = f"sqlite:///{E2E_DB_PATH}"
os.environ["DATABASE_URL_ASYNC"] = f"sqlite+aiosqlite:///{E2E_DB_PATH}"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["GROQ_API_KEY"] = ""
os.environ["STORAGE_BACKEND"] = "local"

# Mock slowapi if needed
from unittest.mock import MagicMock
try:
    import slowapi  # noqa
except ImportError:
    _m = MagicMock()
    _m.Limiter = MagicMock
    _m._rate_limit_exceeded_handler = MagicMock()
    sys.modules.setdefault("slowapi", _m)
    sys.modules.setdefault("slowapi.util", MagicMock())
    sys.modules.setdefault("slowapi.errors", MagicMock())
    sys.modules.setdefault("slowapi.middleware", MagicMock())

from fastapi.testclient import TestClient

# NOTE: No more bcrypt.__about__ patch needed — app/core/security.py now uses
# bcrypt directly via a custom _BcryptContext wrapper, dropping the passlib
# dependency that required the version-introspection shim.

# ─── Now import the app ──────────────────────────────────────────────────────
from app.main import app
from app.core.database import get_db
from app.core.security import verify_token, get_current_user, require_permission, require_plan
from app.core.security import create_access_token
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Disable lifespan (no Redis/DB startup checks)
from contextlib import asynccontextmanager

@asynccontextmanager
async def _noop_lifespan(app):
    yield

app.router.lifespan_context = _noop_lifespan

# ─── Create schema + seed against throwaway DB ──────────────────────────────
print("─── Creating E2E test DB schema ───")
from app.core.database import Base, engine
# Import all model modules so they register with Base.metadata
import importlib
import pkgutil
import app.models as models_pkg
for _, mod_name, _ in pkgutil.iter_modules(models_pkg.__path__):
    importlib.import_module(f"app.models.{mod_name}")
Base.metadata.create_all(bind=engine)
print(f"  Created tables from SQLAlchemy metadata")

# Also ensure operational_tables (raw-SQL DDL) exist
try:
    from app.core.operational_tables import ensure_operational_tables
    ensure_operational_tables(engine)
    print(f"  Ensured operational tables")
except Exception as e:
    print(f"  (operational_tables skipped: {e})")

print("─── Seeding E2E test DB via init_db.py ───")
seed_env = os.environ.copy()
seed_env["DATABASE_URL"] = f"sqlite:///{E2E_DB_PATH}"
seed_env["DATABASE_URL_SYNC"] = f"sqlite:///{E2E_DB_PATH}"
seed_env["DATABASE_URL_ASYNC"] = f"sqlite+aiosqlite:///{E2E_DB_PATH}"
seed_result = subprocess.run(
    [sys.executable, str(SCRIPT_DIR / "init_db.py")],
    cwd=str(BACKEND_DIR),
    env=seed_env,
    capture_output=True,
    text=True,
)
if seed_result.returncode != 0:
    print(seed_result.stdout)
    print(seed_result.stderr)
    raise SystemExit(f"init_db.py exited {seed_result.returncode}")
for line in seed_result.stdout.splitlines():
    if line.strip().startswith(("Created", "Seeded", "Tenant", "✅", "───", "Employees", "Employment", "Payslips", "Leave")):
        print(f"  {line}")

# ─── Read real users from DB ─────────────────────────────────────────────────
db_path = str(E2E_DB_PATH)
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("SELECT id, email, tenant_id FROM users ORDER BY email")
users_data = c.fetchall()
conn.close()

super_admin = None
tenant_admin = None
for uid, email, tenant_id in users_data:
    if email == "admin@guinee-academy.local":
        super_admin = {"id": uid, "email": email, "tenant_id": tenant_id, "role": "SUPER_ADMIN"}
    elif email == "admin@lycee-alpha.gn":
        tenant_admin = {"id": uid, "email": email, "tenant_id": tenant_id, "role": "TENANT_ADMIN"}
    elif email == "prof.mariam@lycee-alpha.gn":
        teacher = {"id": uid, "email": email, "tenant_id": tenant_id, "role": "TEACHER"}

print(f"  Found SUPER_ADMIN: {super_admin['id'] if super_admin else None}")
print(f"  Found TENANT_ADMIN: {tenant_admin['id'] if tenant_admin else None}")

# ─── Build a fake user object that matches what auth deps expect ─────────────
# get_current_user returns a dict with keys: id, email, first_name, last_name,
# username, roles, tenant_id, tenant_name, _token_version
def make_fake_user(user_id, email, tenant_id, role, is_superuser=False):
    roles = [role] if role else []
    if is_superuser and "SUPER_ADMIN" not in roles:
        roles.append("SUPER_ADMIN")
    return {
        "id": user_id,
        "email": email,
        "first_name": "Test",
        "last_name": "User",
        "username": email,
        "roles": roles,
        "tenant_id": tenant_id,
        "tenant_name": "Test Tenant",
        "_token_version": 0,
        "is_active": True,
        "is_superuser": is_superuser,
        "is_verified": True,
        "mfa_enabled": False,
        "must_change_password": False,
    }

def _make_override(user_dict, is_superuser=False):
    def _override():
        return FakeUser(
            user_dict["id"],
            user_dict["email"],
            user_dict["tenant_id"],
            user_dict["role"],
            is_superuser=is_superuser,
        )
    return _override

# Override auth dependencies
def _verify_token_override():
    """Return a fake token payload that satisfies downstream get_current_user."""
    return {"sub": None}  # placeholder; get_current_user override takes over

if super_admin:
    sa_user = make_fake_user(
        super_admin["id"], super_admin["email"], super_admin["tenant_id"],
        super_admin["role"], is_superuser=True,
    )
    ta_user = make_fake_user(
        tenant_admin["id"] if tenant_admin else None,
        tenant_admin["email"] if tenant_admin else None,
        tenant_admin["tenant_id"] if tenant_admin else None,
        tenant_admin["role"] if tenant_admin else None,
    ) if tenant_admin else None

    def _get_current_user_sa():
        return sa_user

    def _get_current_user_ta():
        return ta_user

    app.dependency_overrides[verify_token] = _verify_token_override
    app.dependency_overrides[get_current_user] = _get_current_user_sa

client = TestClient(app, raise_server_exceptions=False)
client.__enter__()

# ─── Helpers ─────────────────────────────────────────────────────────────────
def call(method, path, token=None, json_body=None, params=None, label=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        r = client.request(method, path, headers=headers, json=json_body, params=params)
    except Exception as e:
        print(f"  [ERROR] {label or path}: {e}")
        return False, None

    body_lower = r.text.lower()
    sql_leak_keywords = [
        "no such function: gen_random_uuid",
        "no such function: to_char",
        "no such function: date_trunc",
        "no such function: array_agg",
        "no such function: now()",
        "no such function: current_date",
        'no such function: "filter"',
        "unsupported construct: filter",
        "no such table: information_schema",
        'near "array[": syntax error',
        'near "::": syntax error',
        'near "filter": syntax error',
        'near "interval": syntax error',
        'near "do $$": syntax error',
        'near "do": syntax error',
        'near "cast(": syntax error',
    ]
    sql_leak = any(s in body_lower for s in sql_leak_keywords)
    is_500_with_sqlite = r.status_code == 500 and ("operationalerror" in body_lower or "sqlalchemy" in body_lower)

    if sql_leak:
        marker = "SQL_LEAK"
    elif is_500_with_sqlite:
        marker = "SQL_ERROR"
    elif r.status_code >= 500:
        marker = "SERVER_ERROR"
    else:
        marker = "OK"

    status_str = f"HTTP {r.status_code}"
    if marker != "OK":
        snippet = r.text[:400].replace("\n", " ")
        print(f"  [{marker}] {label or path:48s} -> {status_str}  {snippet}")
    else:
        print(f"  [{marker}] {label or path:48s} -> {status_str}")
    return marker == "OK", r


def main():
    print("=" * 80)
    print("END-TO-END SQLite COMPATIBILITY TEST (TestClient + auth bypass)")
    print("=" * 80)

    # Use any token string (deps are overridden)
    fake_token = "test-bypass-token"
    results = []
    print("\n[1/2] Testing endpoints with SUPER_ADMIN context...")
    # Switch to super admin
    if super_admin:
        app.dependency_overrides[get_current_user] = _get_current_user_sa

    # ── Platform (super admin only) ──────────────────────────────────────────
    print("\n  ── Platform (platform.py) ──")
    ok, _ = call("GET", "/api/v1/platform/tenants/", fake_token, label="platform-tenants")
    results.append(ok)
    ok, _ = call("GET", "/api/v1/platform/stats/", fake_token, label="platform-stats")
    results.append(ok)

    # ── Webhooks (super admin only) ──────────────────────────────────────────
    print("\n  ── Webhooks (webhooks.py: ::text[] + json.dumps) ──")
    ok, _ = call("GET", "/api/v1/webhooks/", fake_token, label="webhooks-list")
    results.append(ok)

    # ── Billing ──────────────────────────────────────────────────────────────
    print("\n  ── Billing (billing.py) ──")
    ok, _ = call("GET", "/api/v1/billing/plans/", fake_token, label="billing-plans")
    results.append(ok)

    print("\n[2/2] Testing endpoints with TENANT_ADMIN context...")
    # Switch to tenant admin
    if tenant_admin:
        app.dependency_overrides[get_current_user] = _get_current_user_ta

    # ── Analytics ────────────────────────────────────────────────────────────
    print("\n  ── Analytics (analytics.py: NULLIF+FILTER+TO_CHAR+INTERVAL+::numeric) ──")
    for path, label in [
        ("/api/v1/analytics/dashboard-kpis/", "dashboard-kpis"),
        ("/api/v1/analytics/ministry-kpis/", "ministry-kpis"),
        ("/api/v1/analytics/ministry-stats/levels/", "ministry-stats-levels"),
        ("/api/v1/analytics/ministry-export/csv/", "ministry-export-csv"),
        ("/api/v1/analytics/revenue-trend/", "revenue-trend"),
        ("/api/v1/analytics/attendance-trend/", "attendance-trend"),
        ("/api/v1/analytics/debt-aging/", "debt-aging"),
        ("/api/v1/analytics/academic-kpis/", "academic-kpis"),
        ("/api/v1/analytics/financial-kpis/", "financial-kpis"),
        ("/api/v1/analytics/operational-kpis/", "operational-kpis"),
        ("/api/v1/analytics/revenue-by-category/", "revenue-by-category"),
        ("/api/v1/analytics/grades-distribution/", "grades-distribution"),
        ("/api/v1/analytics/students-at-risk/", "students-at-risk"),
    ]:
        ok, _ = call("GET", path, fake_token, label=label)
        results.append(ok)

    # ── MFA ──────────────────────────────────────────────────────────────────
    print("\n  ── MFA (mfa.py: sqlite_master/pragma + DDL + INTERVAL) ──")
    for path, label in [
        ("/api/v1/mfa/status/", "mfa-status"),
        ("/api/v1/mfa/backup-codes/count/", "mfa-backup-codes-count"),
    ]:
        ok, _ = call("GET", path, fake_token, label=label)
        results.append(ok)

    # ── Parents ──────────────────────────────────────────────────────────────
    print("\n  ── Parents (aliases.py: GROUP_CONCAT + ARRAY[]::uuid[]) ──")
    ok, _ = call("GET", "/api/v1/parents/", fake_token, label="parents-list")
    results.append(ok)

    # ── Search ───────────────────────────────────────────────────────────────
    print("\n  ── Search (search.py: CAST AS TEXT + SUBSTR) ──")
    ok, _ = call("GET", "/api/v1/search/", fake_token, params={"q": "admin"}, label="search")
    results.append(ok)

    # ── School life ──────────────────────────────────────────────────────────
    print("\n  ── School-life (school_life.py: FILTER→SUM) ──")
    for path, label in [
        ("/api/v1/school-life/attendance/", "school-life-attendance"),
        ("/api/v1/school-life/assessments/", "school-life-assessments"),
        ("/api/v1/school-life/homework/", "school-life-homework"),
    ]:
        ok, _ = call("GET", path, fake_token, label=label)
        results.append(ok)

    # ── Teachers ─────────────────────────────────────────────────────────────
    print("\n  ── Teachers (teachers.py: gen_random_uuid + NOW) ──")
    ok, _ = call("GET", "/api/v1/teachers/", fake_token, label="teachers-list")
    results.append(ok)

    # ── Clubs ────────────────────────────────────────────────────────────────
    print("\n  ── Clubs (clubs.py: gen_random_uuid + NOW) ──")
    ok, _ = call("GET", "/api/v1/clubs/", fake_token, label="clubs-list")
    results.append(ok)

    # ── Incidents ────────────────────────────────────────────────────────────
    print("\n  ── Incidents (incidents.py: gen_random_uuid + NOW + ON CONFLICT) ──")
    ok, _ = call("GET", "/api/v1/incidents/", fake_token, label="incidents-list")
    results.append(ok)

    # ── Library ──────────────────────────────────────────────────────────────
    print("\n  ── Library (library.py: gen_random_uuid + NOW) ──")
    for path, label in [
        ("/api/v1/library/resources/", "library-resources"),
        ("/api/v1/library/categories/", "library-categories"),
    ]:
        ok, _ = call("GET", path, fake_token, label=label)
        results.append(ok)

    # ── Surveys ──────────────────────────────────────────────────────────────
    print("\n  ── Surveys (surveys.py: gen_random_uuid + ::jsonb + NOW) ──")
    ok, _ = call("GET", "/api/v1/surveys/", fake_token, label="surveys-list")
    results.append(ok)

    # ── Communication ────────────────────────────────────────────────────────
    print("\n  ── Communication (communication.py: gen_random_uuid + ::jsonb + NOW) ──")
    for path, label in [
        ("/api/v1/communication/announcements/", "announcements-list"),
        ("/api/v1/communication/notifications/", "notifications-list"),
    ]:
        ok, _ = call("GET", path, fake_token, label=label)
        results.append(ok)

    # ── Payments ─────────────────────────────────────────────────────────────
    print("\n  ── Payments (payments.py: CURRENT_DATE→param) ──")
    for path, label in [
        ("/api/v1/payments/", "payments-list"),
        ("/api/v1/payments/stats/", "payments-stats"),
    ]:
        ok, _ = call("GET", path, fake_token, label=label)
        results.append(ok)

    # ── Payment schedules ────────────────────────────────────────────────────
    print("\n  ── Payment schedules (payment_schedules.py: ::date/::timestamptz) ──")
    ok, _ = call("GET", "/api/v1/payment-schedules/", fake_token, label="payment-schedules-list")
    results.append(ok)

    # ── Students ─────────────────────────────────────────────────────────────
    print("\n  ── Students (students.py: CURRENT_DATE→param) ──")
    ok, _ = call("GET", "/api/v1/students/", fake_token, label="students-list")
    results.append(ok)

    # ── RGPD ─────────────────────────────────────────────────────────────────
    print("\n  ── RGPD (rgpd.py: ::uuid removed) ──")
    ok, _ = call("GET", "/api/v1/rgpd/deletion-requests/", fake_token, label="rgpd-deletion-requests")
    results.append(ok)

    # ── Users ────────────────────────────────────────────────────────────────
    print("\n  ── Users (users.py) ──")
    for path, label in [
        ("/api/v1/users/", "users-list"),
        ("/api/v1/users/me/", "users-me"),
    ]:
        ok, _ = call("GET", path, fake_token, label=label)
        results.append(ok)

    # ── Audit ────────────────────────────────────────────────────────────────
    print("\n  ── Audit (audit.py) ──")
    ok, _ = call("GET", "/api/v1/audit/logs/", fake_token, label="audit-logs")
    results.append(ok)

    # ── Notifications ────────────────────────────────────────────────────────
    print("\n  ── Notifications ──")
    ok, _ = call("GET", "/api/v1/notifications/", fake_token, label="notifications-list")
    results.append(ok)

    # ── Admissions ───────────────────────────────────────────────────────────
    print("\n  ── Admissions (admissions.py: gen_random_uuid + ::jsonb + NOW) ──")
    ok, _ = call("GET", "/api/v1/admissions/", fake_token, label="admissions-list")
    results.append(ok)

    # ── HR ───────────────────────────────────────────────────────────────────
    print("\n  ── HR (hr.py) ──")
    for path, label in [
        ("/api/v1/hr/employees/", "hr-employees"),
        ("/api/v1/hr/contracts/", "hr-contracts"),
        ("/api/v1/hr/leave-requests/", "hr-leave-requests"),
        ("/api/v1/hr/payslips/", "hr-payslips"),
    ]:
        ok, _ = call("GET", path, fake_token, label=label)
        results.append(ok)

    # ── Summary ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    ok = sum(1 for r in results if r)
    fail = sum(1 for r in results if not r)
    total = len(results)
    print(f"  PASSED: {ok}/{total}")
    print(f"  FAILED: {fail}/{total}")
    if fail == 0:
        print("\n  ✅ ALL ENDPOINTS WORK ON SQLITE — no PostgreSQL-only SQL leaked through.")
    else:
        print(f"\n  ⚠️  {fail} endpoints had issues — see above.")
    return 0 if fail == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
