"""
Seed E2E test users for Playwright CI runs.

Creates the 4 test users expected by tests/fixtures/auth.ts on the
default tenant (lycee-alpha). Idempotent — safe to run multiple times.

Created users (all with password `Password123!`):
  - admin@test.local    → TENANT_ADMIN  (also has ADMIN role alias)
  - teacher@test.local  → TEACHER
  - parent@test.local   → PARENT
  - student@test.local  → STUDENT

Usage:
    DATABASE_URL=postgresql://... python scripts/seed_e2e_users.py

Environment variables:
    DATABASE_URL          — SQLAlchemy URL (sqlite or postgresql)
    E2E_TEST_PASSWORD     — password for all test users (default: Password123!)
    E2E_TENANT_SLUG       — tenant slug to attach users to (default: lycee-alpha)
"""
from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime

# Ensure backend/ is importable
HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(HERE)
sys.path.insert(0, BACKEND_DIR)

import bcrypt  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402


# ── Config ────────────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite:///./guinee_academy.db",
)
TEST_PASSWORD = os.environ.get("E2E_TEST_PASSWORD", "Password123!")
TENANT_SLUG = os.environ.get("E2E_TENANT_SLUG", "lycee-alpha")

_IS_SQLITE = DATABASE_URL.startswith("sqlite:")
if not _IS_SQLITE:
    # Normalize async/sync postgres URLs to plain psycopg URL
    for prefix in (
        "postgresql+asyncpg://",
        "postgresql+psycopg2://",
        "postgresql+psycopg://",
    ):
        if DATABASE_URL.startswith(prefix):
            DATABASE_URL = DATABASE_URL.replace(prefix, "postgresql://", 1)
            break
    if not DATABASE_URL.startswith("postgresql+psycopg://"):
        DATABASE_URL = DATABASE_URL.replace(
            "postgresql://", "postgresql+psycopg://", 1
        )

connect_args = {"check_same_thread": False} if _IS_SQLITE else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Users to seed ─────────────────────────────────────────────────────────
E2E_USERS = [
    {
        "email": "admin@test.local",
        "first_name": "E2E",
        "last_name": "Admin",
        "role": "TENANT_ADMIN",
        "username": "admin@test.local",
    },
    {
        "email": "teacher@test.local",
        "first_name": "E2E",
        "last_name": "Teacher",
        "role": "TEACHER",
        "username": "teacher@test.local",
    },
    {
        "email": "parent@test.local",
        "first_name": "E2E",
        "last_name": "Parent",
        "role": "PARENT",
        "username": "parent@test.local",
    },
    {
        "email": "student@test.local",
        "first_name": "E2E",
        "last_name": "Student",
        "role": "STUDENT",
        "username": "student@test.local",
    },
]


def _ensure_tenant(db) -> str:
    """Ensure the lycee-alpha tenant exists. Returns its UUID as a string."""
    row = db.execute(
        text("SELECT id FROM tenants WHERE slug = :slug"),
        {"slug": TENANT_SLUG},
    ).fetchone()
    if row:
        return str(row[0])

    # Create a minimal tenant — only what's strictly required by the schema.
    tenant_id = str(uuid.uuid4())
    now = datetime.utcnow()
    import json
    settings = {
        "landing": {
            "tagline": "E2E test tenant",
            "primary_color": "#1e3a5f",
            "secondary_color": "#0ea5e9",
            "announcements": [],
            "show_programs": True,
            "show_stats": True,
            "show_gallery": True,
        },
        "onboarding_completed": True,
        "onboarding_step": 4,
    }
    db.execute(
        text(
            """
            INSERT INTO tenants
                (id, name, slug, type, is_active, settings, created_at, updated_at, country)
            VALUES
                (:id, :name, :slug, 'high_school', true, :settings, :now, :now, 'GN')
            """
        ),
        {
            "id": tenant_id,
            "name": "Lycée Alpha Conakry",
            "slug": TENANT_SLUG,
            "settings": json.dumps(settings),
            "now": now,
        },
    )
    print(f"  Created tenant: {TENANT_SLUG} ({tenant_id[:8]}...)")
    return tenant_id


def _upsert_user(db, user_def: dict, tenant_id: str, pw_hash: str) -> str:
    """Insert or update a user. Returns its UUID as a string."""
    now = datetime.utcnow()
    existing = db.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": user_def["email"]},
    ).fetchone()

    if existing:
        user_id = str(existing[0])
        # Update password + tenant + active state to ensure consistency
        db.execute(
            text(
                """
                UPDATE users
                SET password_hash = :pw,
                    tenant_id = :tid,
                    is_active = true,
                    is_verified = true,
                    must_change_password = false,
                    updated_at = :now
                WHERE id = :uid
                """
            ),
            {"pw": pw_hash, "tid": tenant_id, "now": now, "uid": user_id},
        )
        print(f"  Updated existing user: {user_def['email']} → {user_def['role']}")
    else:
        user_id = str(uuid.uuid4())
        db.execute(
            text(
                """
                INSERT INTO users
                    (id, email, username, password_hash, first_name, last_name,
                     is_active, is_superuser, tenant_id, created_at, updated_at,
                     is_verified, mfa_enabled, must_change_password)
                VALUES
                    (:id, :email, :username, :pw, :fn, :ln,
                     true, false, :tid, :now, :now,
                     true, false, false)
                """
            ),
            {
                "id": user_id,
                "email": user_def["email"],
                "username": user_def["username"],
                "pw": pw_hash,
                "fn": user_def["first_name"],
                "ln": user_def["last_name"],
                "tid": tenant_id,
                "now": now,
            },
        )
        print(f"  Created user: {user_def['email']} → {user_def['role']}")

    # Ensure role is assigned
    role_row = db.execute(
        text(
            "SELECT id FROM user_roles WHERE user_id = :uid AND role = :role AND tenant_id = :tid"
        ),
        {"uid": user_id, "role": user_def["role"], "tid": tenant_id},
    ).fetchone()
    if not role_row:
        db.execute(
            text(
                """
                INSERT INTO user_roles (id, user_id, role, tenant_id, created_at, updated_at)
                VALUES (:id, :uid, :role, :tid, :now, :now)
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "uid": user_id,
                "role": user_def["role"],
                "tid": tenant_id,
                "now": now,
            },
        )
        print(f"    + Assigned role: {user_def['role']}")

    return user_id


def main() -> int:
    print("\n🌱 Seeding E2E test users...\n")
    db = SessionLocal()
    try:
        tenant_id = _ensure_tenant(db)
        pw_hash = bcrypt.hashpw(
            TEST_PASSWORD.encode(), bcrypt.gensalt()
        ).decode()

        for user_def in E2E_USERS:
            _upsert_user(db, user_def, tenant_id, pw_hash)

        db.commit()

        # Sanity summary
        users = db.execute(text("SELECT COUNT(*) FROM users")).scalar()
        roles = db.execute(text("SELECT COUNT(*) FROM user_roles")).scalar()
        print("\n─── Summary ───")
        print(f"  Total users: {users}")
        print(f"  Total roles: {roles}")
        print(f"\n─── E2E Login Credentials (password: {TEST_PASSWORD}) ───")
        for u in E2E_USERS:
            print(f"  {u['role']:<14} → {u['email']}")
        print("\n✅ E2E users seeded successfully!\n")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"\n❌ Error during E2E seed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
