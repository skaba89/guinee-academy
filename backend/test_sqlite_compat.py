#!/usr/bin/env python3
"""
SQLite Compatibility Test Script for Guinée Academy Backend.
Tests all user endpoints that were fixed for SQLite compatibility.

This script:
1. Creates a fresh SQLite DB
2. Starts a TestClient
3. Logs in as SUPER_ADMIN
4. Creates a tenant
5. Creates a user (TENANT_ADMIN)
6. Lists users
7. Gets user profile
8. Prints results for each step
"""
import os
import sys
import uuid

# ─── Force SQLite mode before ANY app imports ─────────────────────────────────
os.environ["DEBUG"] = "True"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only-32chars"
os.environ["DATABASE_URL"] = "sqlite:///./test_sqlite_compat.db"
os.environ["DATABASE_URL_SYNC"] = "sqlite:///./test_sqlite_compat.db"
os.environ["DATABASE_URL_ASYNC"] = "sqlite+aiosqlite:///./test_sqlite_compat.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["BOOTSTRAP_SECRET"] = "test-bootstrap-secret-that-is-at-least-32-characters-long"
os.environ["ADMIN_DEFAULT_PASSWORD"] = "Admin@2024!Strong"

# Mock slowapi if not installed
try:
    import slowapi  # noqa: F401
except ImportError:
    from unittest.mock import MagicMock
    _mock_slowapi = MagicMock()
    _mock_slowapi.Limiter = MagicMock
    _mock_slowapi._rate_limit_exceeded_handler = MagicMock()
    sys.modules.setdefault("slowapi", _mock_slowapi)
    sys.modules.setdefault("slowapi.util", MagicMock())
    sys.modules.setdefault("slowapi.errors", MagicMock())
    sys.modules.setdefault("slowapi.middleware", MagicMock())

# Remove stale test DB if it exists
db_path = os.path.join(os.path.dirname(__file__), "test_sqlite_compat.db")
if os.path.exists(db_path):
    os.remove(db_path)

from app.core.config import settings

print(f"\n{'='*70}")
print(f"  SQLite Compatibility Test")
print(f"{'='*70}")
print(f"  is_sqlite = {settings.is_sqlite}")
print(f"  DATABASE_URL_SYNC = {settings.DATABASE_URL_SYNC}")
print(f"{'='*70}\n")

assert settings.is_sqlite, "Test must run with SQLite! Check DATABASE_URL_SYNC."

# ─── Create tables and seed data using ORM ────────────────────────────────────
from app.core.database import engine, SessionLocal
from app.models.base import Base

# Import all models so they register with Base.metadata
import app.models  # noqa: F401

# Create all tables
Base.metadata.create_all(bind=engine)
print("✅ Step 0: Tables created in SQLite")

# Seed a SUPER_ADMIN user and a tenant using ORM
from app.models.user import User
from app.models.user_role import UserRole
from app.models.tenant import Tenant
from app.core.security import get_password_hash
from datetime import datetime, timezone

db = SessionLocal()

# Create tenant
tenant_id = str(uuid.uuid4())
tenant = Tenant(
    id=tenant_id,
    name="École Test",
    slug="ecole-test",
    type="SCHOOL",
    country="GN",
    currency="GNF",
    timezone="Africa/Conakry",
    email="contact@ecole-test.gn",
    is_active=True,
)
db.add(tenant)
db.flush()

# Create SUPER_ADMIN user
super_admin_id = str(uuid.uuid4())
super_admin_pw = "Admin@2024!Strong"
super_admin = User(
    id=super_admin_id,
    email="superadmin@guinee-academy.local",
    username="superadmin",
    first_name="Super",
    last_name="Admin",
    password_hash=get_password_hash(super_admin_pw),
    is_active=True,
    is_superuser=True,
    mfa_enabled=False,
    must_change_password=False,
    tenant_id=None,  # SUPER_ADMIN has no tenant
)
db.add(super_admin)
db.flush()

# Assign SUPER_ADMIN role
super_admin_role = UserRole(
    id=str(uuid.uuid4()),
    user_id=super_admin_id,
    role="SUPER_ADMIN",
    tenant_id=None,
)
db.add(super_admin_role)
db.commit()

print(f"✅ Step 1: SUPER_ADMIN created (id={super_admin_id})")
print(f"   Tenant created (id={tenant_id})")
db.close()

# ─── Set up TestClient ────────────────────────────────────────────────────────
from contextlib import asynccontextmanager
from fastapi.testclient import TestClient
from app.main import app

@asynccontextmanager
async def _noop_lifespan(app):
    yield

original_lifespan = app.router.lifespan_context
app.router.lifespan_context = _noop_lifespan

client = TestClient(app, raise_server_exceptions=True)

# ─── Step 2: Login as SUPER_ADMIN ────────────────────────────────────────────
print("\n--- Step 2: Login as SUPER_ADMIN ---")
login_resp = client.post(
    "/api/v1/auth/login/",
    data={"username": "superadmin@guinee-academy.local", "password": super_admin_pw},
    headers={"Content-Type": "application/x-www-form-urlencoded"},
)
print(f"  Status: {login_resp.status_code}")
if login_resp.status_code != 200:
    print(f"  Error: {login_resp.text}")
    sys.exit(1)
token_data = login_resp.json()
access_token = token_data.get("access_token")
print(f"  Token: {access_token[:30]}...")

auth_headers = {
    "Authorization": f"Bearer {access_token}",
    "X-Tenant-ID": tenant_id,
}

# ─── Step 3: GET /users/me/ (Bug #3 - LEFT JOIN tenant) ──────────────────────
print("\n--- Step 3: GET /users/me/ (LEFT JOIN tenant fix) ---")
me_resp = client.get("/api/v1/users/me/", headers=auth_headers)
print(f"  Status: {me_resp.status_code}")
if me_resp.status_code != 200:
    print(f"  Error: {me_resp.text}")
else:
    me_data = me_resp.json()
    print(f"  User: {me_data.get('user', {}).get('email')}")
    print(f"  Roles: {me_data.get('roles')}")
    print(f"  Tenant: {me_data.get('tenant', {}).get('name') if me_data.get('tenant') else 'None'}")

# ─── Step 4: POST /users/ (Bug #1 - NOW() + ON CONFLICT) ────────────────────
print("\n--- Step 4: POST /users/ (create TENANT_ADMIN - NOW() + role insert fix) ---")
create_resp = client.post(
    "/api/v1/users/",
    json={
        "email": "tenantadmin@ecole-test.gn",
        "first_name": "Tenant",
        "last_name": "Admin",
        "password": "Admin@2024!Strong",
        "roles": ["TENANT_ADMIN"],
    },
    headers=auth_headers,
)
print(f"  Status: {create_resp.status_code}")
if create_resp.status_code != 201:
    print(f"  Error: {create_resp.text}")
else:
    create_data = create_resp.json()
    new_user_id = create_data.get("id")
    print(f"  Created user id: {new_user_id}")

# ─── Step 5: GET /users/ (Bug #2 - ARRAY_AGG/CONCAT/::text) ─────────────────
print("\n--- Step 5: GET /users/ (list users - ARRAY_AGG/GROUP_CONCAT fix) ---")
list_resp = client.get("/api/v1/users/", headers=auth_headers)
print(f"  Status: {list_resp.status_code}")
if list_resp.status_code != 200:
    print(f"  Error: {list_resp.text}")
else:
    list_data = list_resp.json()
    items = list_data.get("items", [])
    print(f"  Total users: {list_data.get('total')}")
    for u in items:
        print(f"  - {u.get('email')}: roles={u.get('roles')}")

# ─── Step 6: GET /users/{user_id}/ (Single user fetch) ──────────────────────
print("\n--- Step 6: GET /users/{user_id}/ (single user fetch) ---")
if create_resp.status_code == 201:
    get_resp = client.get(f"/api/v1/users/{new_user_id}/", headers=auth_headers)
    print(f"  Status: {get_resp.status_code}")
    if get_resp.status_code != 200:
        print(f"  Error: {get_resp.text}")
    else:
        get_data = get_resp.json()
        print(f"  User: {get_data.get('email')}, roles={get_data.get('roles')}")

# ─── Step 7: PATCH /users/{user_id}/ (Bug #7 - NOW() in UPDATE) ─────────────
print("\n--- Step 7: PATCH /users/{user_id}/ (update user - CURRENT_TIMESTAMP fix) ---")
if create_resp.status_code == 201:
    patch_resp = client.patch(
        f"/api/v1/users/{new_user_id}/",
        json={"first_name": "Updated"},
        headers=auth_headers,
    )
    print(f"  Status: {patch_resp.status_code}")
    if patch_resp.status_code != 200:
        print(f"  Error: {patch_resp.text}")
    else:
        print(f"  Result: {patch_resp.json()}")

# ─── Step 8: PATCH /users/{user_id}/toggle-status/ (Bug #8 - NOW()) ─────────
print("\n--- Step 8: PATCH toggle-status (CURRENT_TIMESTAMP fix) ---")
if create_resp.status_code == 201:
    toggle_resp = client.patch(
        f"/api/v1/users/{new_user_id}/toggle-status/",
        json={"is_active": False},
        headers=auth_headers,
    )
    print(f"  Status: {toggle_resp.status_code}")
    if toggle_resp.status_code != 200:
        print(f"  Error: {toggle_resp.text}")
    else:
        print(f"  Result: {toggle_resp.json()}")

    # Re-enable the user
    client.patch(
        f"/api/v1/users/{new_user_id}/toggle-status/",
        json={"is_active": True},
        headers=auth_headers,
    )

# ─── Step 9: GET /users/roles/ (Bug #2 - CONCAT/::text) ────────────────────
print("\n--- Step 9: GET /users/roles/ (CONCAT/::text fix) ---")
roles_resp = client.get("/api/v1/users/roles/", headers=auth_headers)
print(f"  Status: {roles_resp.status_code}")
if roles_resp.status_code != 200:
    print(f"  Error: {roles_resp.text}")
else:
    roles_data = roles_resp.json()
    print(f"  Role assignments: {len(roles_data)}")
    for r in roles_data[:5]:
        print(f"  - {r.get('id')}: user={r.get('user_id')}, role={r.get('role')}")

# ─── Step 10: POST /users/roles/ (Bug #4 - NOW() + ON CONFLICT) ─────────────
print("\n--- Step 10: POST /users/roles/ (assign role - CURRENT_TIMESTAMP + ON CONFLICT fix) ---")
if create_resp.status_code == 201:
    assign_resp = client.post(
        "/api/v1/users/roles/",
        json={
            "user_id": new_user_id,
            "role": "TEACHER",
            "tenant_id": tenant_id,
        },
        headers=auth_headers,
    )
    print(f"  Status: {assign_resp.status_code}")
    if assign_resp.status_code != 201:
        print(f"  Error: {assign_resp.text}")
    else:
        print(f"  Result: {assign_resp.json()}")

# ─── Step 11: PUT /users/{user_id}/roles/ (Bug #5 - NOW() + ON CONFLICT) ────
print("\n--- Step 11: PUT /users/{user_id}/roles/ (replace roles - ON CONFLICT fix) ---")
if create_resp.status_code == 201:
    put_roles_resp = client.put(
        f"/api/v1/users/{new_user_id}/roles/",
        json={"roles": ["TENANT_ADMIN", "TEACHER"]},
        headers=auth_headers,
    )
    print(f"  Status: {put_roles_resp.status_code}")
    if put_roles_resp.status_code != 200:
        print(f"  Error: {put_roles_resp.text}")
    else:
        print(f"  Result: {put_roles_resp.json()}")

# ─── Step 12: POST /users/{user_id}/roles/ (Bug #6 - NOW() + ON CONFLICT) ───
print("\n--- Step 12: POST /users/{user_id}/roles/ (assign single role - ON CONFLICT fix) ---")
if create_resp.status_code == 201:
    # First remove TEACHER role so we can re-assign it
    client.delete(f"/api/v1/users/{new_user_id}/roles/TEACHER", headers=auth_headers)
    single_role_resp = client.post(
        f"/api/v1/users/{new_user_id}/roles/",
        json={"role": "TEACHER"},
        headers=auth_headers,
    )
    print(f"  Status: {single_role_resp.status_code}")
    if single_role_resp.status_code != 200:
        print(f"  Error: {single_role_resp.text}")
    else:
        print(f"  Result: {single_role_resp.json()}")

# ─── Step 13: GET /users/profiles/ (profiles list with GROUP_CONCAT) ────────
print("\n--- Step 13: GET /users/profiles/ (profiles list - array_agg/GROUP_CONCAT fix) ---")
profiles_resp = client.get("/api/v1/users/profiles/", headers=auth_headers)
print(f"  Status: {profiles_resp.status_code}")
if profiles_resp.status_code != 200:
    print(f"  Error: {profiles_resp.text}")
else:
    profiles_data = profiles_resp.json()
    print(f"  Profile count: {len(profiles_data)}")
    for p in profiles_data[:5]:
        print(f"  - {p.get('email')}: roles={p.get('roles')}")

# ─── Step 14: PATCH /users/profiles/{user_id}/ (Bug #11 - NOW()) ────────────
print("\n--- Step 14: PATCH /users/profiles/{user_id}/ (profile update - CURRENT_TIMESTAMP fix) ---")
profile_patch_resp = client.patch(
    f"/api/v1/users/profiles/{new_user_id}/",
    json={"bio": "Test bio for SQLite compat"},
    headers=auth_headers,
)
print(f"  Status: {profile_patch_resp.status_code}")
if profile_patch_resp.status_code != 200:
    print(f"  Error: {profile_patch_resp.text}")
else:
    print(f"  Result: {profile_patch_resp.json()}")

# ─── Cleanup ─────────────────────────────────────────────────────────────────
app.router.lifespan_context = original_lifespan

# Remove test DB
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"\n🧹 Cleaned up test database: {db_path}")

print(f"\n{'='*70}")
print(f"  ✅ SQLite Compatibility Test Complete!")
print(f"{'='*70}\n")
