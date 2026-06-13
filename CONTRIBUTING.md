# Contributing to Guinée Academy

Welcome to **Guinée Academy** — a multi-tenant SaaS school management platform serving private, public, and institutional schools. We are thrilled that you want to contribute! This guide covers everything you need to get started, write quality code, and submit your work.

---

## Table of Contents

1. [Welcome & Code of Conduct](#welcome--code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Workflow](#development-workflow)
4. [Project Structure](#project-structure)
5. [Frontend Development](#frontend-development)
6. [Backend Development](#backend-development)
7. [Database Migrations](#database-migrations)
8. [Testing](#testing)
9. [Code Quality](#code-quality)
10. [Security Guidelines](#security-guidelines)
11. [Internationalization](#internationalization)
12. [Release Process](#release-process)

---

## Welcome & Code of Conduct

We are committed to providing a welcoming and inclusive experience for everyone. By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please be respectful, constructive, and professional in all interactions — whether in issues, pull requests, code reviews, or discussions.

If you witness or experience unacceptable behavior, please report it to the project maintainers privately. We take all reports seriously and will respond promptly.

---

## Getting Started

### Prerequisites

Before you begin, ensure you have the following tools installed on your system:

| Tool | Version | Purpose |
|------|---------|---------|
| **Docker** + Docker Compose v2+ | Latest | Running infrastructure services |
| **Node.js** | 20.x (see `.nvmrc`) | Frontend build & dev server |
| **Python** | 3.11+ | Backend API |
| **Git** | 2.40+ | Version control |

Optional but recommended:

- **pgAdmin 4** — Database management (included in Docker Compose)
- **MinIO Client (mc)** — S3-compatible storage management

### Fork and Clone

1. **Fork** the repository on GitHub: `https://github.com/skaba89/guinee-academy`
2. **Clone** your fork locally:

```bash
git clone https://github.com/YOUR_USERNAME/guinee-academy.git
cd guinee-academy
```

3. **Add the upstream remote** to stay in sync with the main repository:

```bash
git remote add upstream https://github.com/skaba89/guinee-academy.git
```

### Environment Setup

#### Docker Compose (Recommended)

The fastest way to get the full stack running is with Docker Compose:

```bash
# 1. Copy the environment template
cp .env.docker.example .env.docker

# 2. Generate secrets and edit .env.docker
# At minimum, set these values:
#   SECRET_KEY=<run: openssl rand -hex 32>
#   POSTGRES_PASSWORD=<strong password>
#   MINIO_ROOT_PASSWORD=<strong password, 8+ chars>
#   PGADMIN_PASSWORD=<strong password>

# 3. Start all services
docker compose --env-file .env.docker up -d

# 4. Run database migrations
docker compose exec api alembic upgrade head

# 5. Create the default SUPER_ADMIN account
docker compose exec api python -m app.scripts.create_admin
```

After setup, the following services are available:

| Service | URL |
|---------|-----|
| Frontend (Docker) | http://localhost:3000 |
| API (FastAPI) | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| PgAdmin | http://localhost:5050 |
| MinIO Console | http://localhost:9001 |

#### Local Development (Without Docker for App Code)

If you prefer running the frontend and backend locally with only infrastructure in Docker:

```bash
# Start infrastructure only
docker compose --env-file .env.docker up -d postgres redis minio

# --- Backend ---
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # Edit .env with your local settings
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# --- Frontend (in a separate terminal) ---
npm install
npm run dev                # Vite dev server at http://localhost:5173
```

---

## Development Workflow

### Branch Naming

All branches must follow these naming conventions:

| Prefix | Purpose | Example |
|--------|---------|---------|
| `feat/` | New feature | `feat/student-bulk-import` |
| `fix/` | Bug fix | `fix/grade-calculation-rounding` |
| `docs/` | Documentation only | `docs/api-endpoint-reference` |
| `chore/` | Maintenance, tooling, dependencies | `chore/update-dependencies` |
| `refactor/` | Code refactoring (no behavior change) | `refactor/extract-auth-utils` |
| `test/` | Adding or updating tests | `test/attendance-edge-cases` |
| `security/` | Security fixes | `security/input-validation-hardening` |

### Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) for clear, automated changelogs and semantic versioning:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`

**Examples:**

```
feat(students): add bulk import from CSV
fix(grades): correct weighted average calculation for term grades
docs(api): update authentication flow documentation
chore(deps): bump SQLAlchemy to 2.0.36
security(auth): validate X-Tenant-ID header as UUID before RLS set_config
```

### Pull Request Process

1. **Create a feature branch** from `main` using the naming convention above.
2. **Write code** following the style guides in this document.
3. **Add or update tests** for your changes. All existing tests must pass.
4. **Update documentation** if you are adding new features, API endpoints, or changing behavior.
5. **Submit a PR** with a clear title and description following the Conventional Commits format.
6. **Request review** from at least one maintainer.
7. **Address review feedback** and push fixes to the same branch.
8. **Squash and merge** once approved — maintainers will handle the final merge.

**PR Checklist:**

- [ ] Code compiles and passes lint/type checks
- [ ] All tests pass (backend + frontend + E2E)
- [ ] No secrets or credentials committed
- [ ] New features have corresponding tests
- [ ] API changes are reflected in OpenAPI schema
- [ ] i18n keys added for any new user-facing text

---

## Project Structure

```
guinee-academy/
├── backend/                        # FastAPI backend application
│   ├── app/
│   │   ├── api/v1/                 # API version 1
│   │   │   ├── endpoints/
│   │   │   │   ├── core/           # Core endpoints (auth, users, tenants, health, billing, AI, MFA, storage, etc.)
│   │   │   │   ├── academic/       # Academic endpoints (students, grades, attendance, subjects, levels, etc.)
│   │   │   │   ├── finance/        # Finance endpoints (payments, payment schedules)
│   │   │   │   ├── operational/    # Operational endpoints (HR, school life, admissions, schedule, library, etc.)
│   │   │   │   └── aliases.py      # Frontend-compatibility alias routes
│   │   │   └── router.py           # Main API router that assembles all sub-routers
│   │   ├── core/                   # Core application modules
│   │   │   ├── config.py           # Pydantic Settings (all environment variables)
│   │   │   ├── database.py         # SQLAlchemy engine, SessionLocal, RLS context
│   │   │   ├── security.py         # JWT creation/verification, password hashing, role permissions
│   │   │   ├── cache.py            # Redis async client with SFP: key prefix
│   │   │   ├── storage.py          # MinIO S3 client for file uploads
│   │   │   ├── exceptions.py       # Structured error hierarchy (GuineeAcademyException, NotFoundError, etc.)
│   │   │   ├── events.py           # FastAPI lifespan event handlers
│   │   │   └── logging_config.py   # Structured logging setup
│   │   ├── models/                 # SQLAlchemy ORM models (35+ models)
│   │   │   ├── base.py             # UUIDMixin, TimestampMixin, TenantMixin, GUID type
│   │   │   ├── tenant.py           # Tenant model with Stripe billing fields
│   │   │   ├── user.py             # User model with MFA support
│   │   │   ├── student.py          # Student model
│   │   │   └── ...                 # 30+ additional models
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   ├── crud/                   # Database query helper functions
│   │   ├── middlewares/            # ASGI middleware stack
│   │   │   ├── tenant.py           # Tenant isolation (X-Tenant-ID, JWT tenant_id, RLS context)
│   │   │   ├── metrics.py          # Prometheus metrics (request count, duration, active connections)
│   │   │   ├── quota.py            # Per-tenant resource quota enforcement
│   │   │   └── request_id.py       # X-Request-ID propagation
│   │   ├── services/               # Business logic services
│   │   │   ├── notifications.py    # Multi-channel notification service
│   │   │   ├── payment_gateways.py # Stripe integration
│   │   │   ├── groq_service.py     # AI chat service (Groq)
│   │   │   └── realtime.py         # WebSocket / SSE real-time events
│   │   └── utils/
│   │       └── audit.py            # Audit trail utilities
│   ├── alembic/                    # Database migration engine
│   │   ├── versions/               # Migration scripts (chronological)
│   │   └── env.py                  # Alembic environment configuration
│   ├── scripts/                    # Utility scripts
│   │   ├── create_admin.py         # Bootstrap SUPER_ADMIN account
│   │   ├── seed_demo_tenants.py    # Seed demo data for testing
│   │   └── diagnose_login.py       # Login troubleshooting helper
│   ├── tests/                      # Backend test suite (pytest)
│   ├── pyproject.toml              # Ruff, mypy, pytest, coverage config
│   ├── requirements.txt            # Python dependencies
│   └── Dockerfile.dev              # Development Docker image
│
├── src/                            # React frontend application
│   ├── api/                        # API client (Axios)
│   │   └── client.ts               # Axios instance with interceptors
│   ├── components/                 # React components (~300+ files)
│   │   ├── ui/                     # shadcn/ui base components (Button, Dialog, Table, etc.)
│   │   ├── layouts/                # Role-based layout wrappers (Admin, Teacher, Student, Parent, etc.)
│   │   ├── settings/               # Settings panels (Branding, Security, Finance, etc.)
│   │   ├── dashboard/              # Dashboard widgets, charts, KPI cards
│   │   ├── students/               # Student management components
│   │   ├── grades/                 # Grade management components
│   │   ├── attendance/             # Attendance tracking components
│   │   ├── human-resources/        # HR module components
│   │   ├── badges/                 # Student badge / QR code system
│   │   ├── schedule/               # Timetable components
│   │   ├── messages/               # Real-time messaging
│   │   ├── ai/                     # AI chat widget
│   │   ├── auth/                   # 2FA setup, verification, backup codes
│   │   └── ...                     # Many more domain-specific components
│   ├── contexts/                   # React Context providers
│   │   ├── AuthContext.tsx          # Authentication state (JWT, user, roles)
│   │   ├── TenantContext.tsx        # Current tenant state
│   │   └── ThemeContext.tsx         # Dark/light theme toggle
│   ├── hooks/                      # Custom React hooks (~45 hooks)
│   │   ├── queries/                # TanStack React Query hooks (useStudents, useTeachers, etc.)
│   │   └── __tests__/              # Hook unit tests
│   ├── queries/                    # React Query hook definitions
│   ├── routes/                     # Role-based route definitions (Admin, Teacher, Student, Parent, etc.)
│   ├── pages/                      # Page-level components (~95+ files)
│   ├── features/                   # Feature-based modules (students, etc.)
│   ├── lib/                        # Utility libraries
│   │   ├── utils.ts                # General utilities (cn, formatters)
│   │   ├── permissions.ts          # Frontend permission checks
│   │   ├── validation.ts           # Zod validation utilities
│   │   ├── schemas/                # Zod schemas (student, grade, attendance, etc.)
│   │   ├── i18n/                   # i18next configuration and locale files
│   │   ├── pdf/                    # PDF generation utilities
│   │   ├── security.ts             # Client-side security helpers
│   │   ├── db.ts                   # Dexie offline database
│   │   └── ...                     # More utility modules
│   ├── utils/                      # Additional utility functions (formatters, PDF generators, risk assessment)
│   ├── types/                      # TypeScript type definitions
│   ├── i18n/                       # Alternative i18n setup (locales + config)
│   ├── App.tsx                     # Root application component
│   ├── main.tsx                    # Application entry point
│   └── index.css                   # Tailwind CSS base styles
│
├── tests/                          # End-to-end test suite (Playwright)
│   ├── e2e/                        # E2E test specs
│   │   ├── auth.spec.ts            # Authentication flow tests
│   │   ├── rbac.spec.ts            # Role-based access control tests
│   │   ├── tenant-isolation.spec.ts # Multi-tenancy isolation tests
│   │   ├── students.spec.ts        # Student CRUD tests
│   │   ├── attendance.spec.ts      # Attendance tracking tests
│   │   ├── finance.spec.ts         # Financial operations tests
│   │   ├── badges-*.spec.ts        # Badge system tests (auth, display, security, notifications)
│   │   ├── global-setup.ts         # Playwright global setup
│   │   └── global-teardown.ts      # Playwright global teardown
│   ├── fixtures/                   # Test fixtures (auth helpers)
│   └── utils/                      # Test data utilities
│
├── docker/                         # Docker configuration files
│   ├── nginx.conf                  # Nginx reverse proxy config
│   ├── nginx-main.conf             # Nginx main config
│   ├── nginx.render.conf.template  # Render-specific Nginx template
│   └── gen_keys.py                 # VAPID key generation for push notifications
│
├── scripts/                        # System-level scripts
│   ├── backup-database.sh          # PostgreSQL backup script
│   ├── verify-project.sh           # Project verification script
│   ├── prepare-release.sh          # Release preparation
│   └── test-*.cjs                  # API endpoint test scripts
│
├── docs/                           # Project documentation
├── download/                       # Generated audit/deployment PDFs
├── load-tests/                     # K6 load testing scripts
├── public/                         # Static assets (PWA icons, service worker)
│
├── docker-compose.yml              # Local Docker Compose stack
├── Dockerfile                      # Frontend production Docker image
├── Dockerfile.render               # Render-specific Docker image
├── render.yaml                     # Render.com deployment blueprint
├── netlify.toml                    # Netlify deployment config
├── Makefile                        # Developer convenience commands
├── package.json                    # Frontend dependencies and scripts
├── vite.config.ts                  # Vite build configuration
├── vitest.config.ts                # Vitest test configuration
├── vitest.setup.ts                 # Vitest test setup (jsdom, matchers)
├── playwright.config.ts            # Playwright E2E test configuration
├── eslint.config.js                # ESLint flat config
├── tailwind.config.ts              # Tailwind CSS configuration
├── tsconfig.json                   # TypeScript configuration
└── .env.example                    # Environment variable template (frontend)
```

---

## Frontend Development

### Component Conventions

Guinée Academy uses **React 18** with **TypeScript** and **shadcn/ui** as the component library. All UI components follow these conventions:

1. **File naming:** Use PascalCase for component files (e.g., `StudentFormDialog.tsx`, `GradeTable.tsx`).
2. **Component structure:** One component per file. Export the component as the default export.
3. **shadcn/ui components:** Base UI primitives live in `src/components/ui/`. Never modify these directly — use the shadcn CLI (`npx shadcn-ui add <component>`) to add or update them.
4. **Domain components:** Place feature-specific components in their own directory under `src/components/` (e.g., `students/`, `grades/`, `attendance/`, `human-resources/`).
5. **Layout components:** Role-based layouts are in `src/components/layouts/` (e.g., `AdminLayout.tsx`, `TeacherLayout.tsx`).

```tsx
// Example: Creating a new component
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useTranslation } from "react-i18next";

interface StudentSummaryProps {
  studentId: string;
  studentName: string;
  gpa: number;
}

export function StudentSummary({ studentId, studentName, gpa }: StudentSummaryProps) {
  const { t } = useTranslation();
  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("students.summary.title")}</CardTitle>
      </CardHeader>
      <CardContent>
        <p>{studentName} — GPA: {gpa.toFixed(2)}</p>
      </CardContent>
    </Card>
  );
}
```

### State Management Patterns

The project uses a hybrid state management approach:

| Pattern | Tool | Use Case |
|---------|------|----------|
| **Server state** | TanStack React Query v5 | All API data fetching, caching, and synchronization |
| **Client state** | Zustand v5 | UI state, sidebar toggles, command palette |
| **Auth/Tenant state** | React Context | Authentication, tenant selection, theme |

**React Query conventions:**

- Define query hooks in `src/queries/` or `src/hooks/queries/`
- Use `useQuery` for reads and `useMutation` for writes
- Use optimistic updates for responsive UI (see `src/lib/optimisticUpdate.ts`)
- Query keys are centralized in `src/lib/queryKeys.ts`

```tsx
// Example: Query hook pattern
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/api/client";

export function useStudents(page: number = 1, search: string = "") {
  return useQuery({
    queryKey: ["students", page, search],
    queryFn: async () => {
      const { data } = await apiClient.get("/students", { params: { page, search } });
      return data;
    },
  });
}
```

### Internationalization (i18n)

All user-facing text must use the `useTranslation` hook from `react-i18next`. See the [Internationalization](#internationalization) section below for detailed conventions.

### Testing (Vitest)

Frontend unit tests use **Vitest** with **React Testing Library**:

```bash
# Run all frontend tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage report
npm run test:coverage

# Type-check without emitting
npm run type-check
```

Test file placement:
- Co-locate tests with components: `src/components/__tests__/ComponentName.test.tsx`
- Hook tests: `src/hooks/__tests__/hookName.test.tsx`
- Feature tests: `src/features/students/services/__tests__/service.test.ts`

---

## Backend Development

### API Endpoint Conventions

All API endpoints live under `backend/app/api/v1/endpoints/` and are organized by domain:

| Directory | Domain | Examples |
|-----------|--------|----------|
| `core/` | Core platform | `auth.py`, `users.py`, `tenants.py`, `health.py`, `billing.py`, `mfa.py`, `ai.py` |
| `academic/` | Academic operations | `students.py`, `grades.py`, `attendance.py`, `subjects.py`, `levels.py` |
| `finance/` | Financial operations | `payments.py`, `payment_schedules.py` |
| `operational/` | School operations | `hr.py`, `school_life.py`, `admissions.py`, `schedule.py`, `library.py` |

**Endpoint file pattern:**

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_permission
from app.schemas.student import StudentCreate, StudentUpdate, StudentOut
from app.models.student import Student

router = APIRouter()

@router.get("/", response_model=list[StudentOut])
async def list_students(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("students:read")),
):
    """List all students for the current tenant."""
    ...
```

Key conventions:
- Use `Depends(get_db)` for database sessions (RLS context is set automatically)
- Use `Depends(require_permission("resource:action"))` for authorization
- Use `Depends(require_plan("pro"))` for plan-gated features
- All tenant-scoped queries are automatically filtered by PostgreSQL RLS
- Return Pydantic schemas, never raw ORM models

### Model and Schema Patterns

**Models** (`backend/app/models/`):

Every model inherits from `Base`, `UUIDMixin`, and `TimestampMixin`. Tenant-scoped models also inherit from `TenantMixin`:

```python
from app.models.base import Base, UUIDMixin, TimestampMixin, TenantMixin

class Student(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "students"
    # ... columns
```

The mixins provide:
- `UUIDMixin`: UUID primary key (`id`)
- `TimestampMixin`: `created_at` and `updated_at` columns
- `TenantMixin`: `tenant_id` foreign key with index and CASCADE delete

**Schemas** (`backend/app/schemas/`):

Use Pydantic v2 models for request/response validation:

```python
from pydantic import BaseModel, Field
from datetime import date

class StudentCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: date
    gender: str = Field(..., pattern="^(M|F|Other)$")

class StudentOut(StudentCreate):
    id: str
    tenant_id: str
    matricule: str | None = None

    model_config = {"from_attributes": True}
```

### Testing (pytest)

Backend tests use **pytest** with async support:

```bash
# Run all backend tests
cd backend && pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_students.py

# Run only unit tests (no DB required)
pytest -m unit

# Run only integration tests (requires DB)
pytest -m integration

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Run security-focused tests
pytest -m security
```

Test markers available (defined in `pyproject.toml`):
- `@pytest.mark.unit` — Pure unit tests, no DB or network
- `@pytest.mark.integration` — Integration tests requiring database
- `@pytest.mark.security` — Security-focused tests
- `@pytest.mark.slow` — Long-running tests (deselect with `-m "not slow"`)
- `@pytest.mark.asyncio` — Async tests (auto-enabled via `asyncio_mode = "auto"`)

---

## Database Migrations

We use **Alembic** for all database schema changes. Never modify the schema directly — always create a migration.

### Common Alembic Commands

```bash
# Apply all pending migrations
alembic upgrade head

# Rollback the most recent migration
alembic downgrade -1

# Show current migration version
alembic current

# Show migration history
alembic history --verbose

# Create a new migration (autogenerate from model changes)
alembic revision --autogenerate -m "add_student_email_column"

# Create an empty migration (for manual SQL)
alembic revision -m "add_rls_policy_for_new_table"
```

When using Docker:

```bash
docker compose exec api alembic upgrade head
docker compose exec api alembic revision --autogenerate -m "description"
```

### Creating Migrations

1. **Modify your SQLAlchemy model** in `backend/app/models/`.
2. **Generate the migration:**

```bash
cd backend
alembic revision --autogenerate -m "add_new_field_to_student"
```

3. **Review the generated migration** in `backend/alembic/versions/`. **Never blindly trust autogenerate** — always verify the `upgrade()` and `downgrade()` functions.
4. **Apply the migration:**

```bash
alembic upgrade head
```

### Migration Naming Convention

Migration files are named with a timestamp prefix: `YYYYMMDD_HHMM_description.py`

For RLS-related migrations, include "rls" in the description (e.g., `20260424_0002_rls_operational_tables.py`).

### Important Notes

- Migrations run in production during CI/CD deployment
- Always provide a `downgrade()` function that safely reverses the `upgrade()`
- For RLS policies, write raw SQL in the migration — Alembic autogenerate does not detect RLS
- Test migrations against a clean database: `alembic downgrade base && alembic upgrade head`

---

## Testing

### Backend Tests (pytest)

```bash
cd backend

# All tests
pytest

# With coverage (minimum 50% enforced)
pytest --cov=app

# Specific test file
pytest tests/test_auth.py -v

# Skip slow tests
pytest -m "not slow"

# Run only security tests
pytest -m security
```

**Coverage thresholds** (configured in `pyproject.toml`):
- Minimum: 50% (current baseline, will increase over time)
- Branch coverage is enabled
- `app/main.py` and `app/core/config.py` are excluded from coverage requirements

### Frontend Tests (Vitest)

```bash
# All tests
npm test

# Watch mode
npm run test:watch

# With coverage
npm run test:coverage

# UI mode
npx vitest --ui
```

**Coverage thresholds** (configured in `vitest.config.ts`):
- Lines: 25%
- Functions: 25%
- Branches: 20%
- Statements: 25%

### End-to-End Tests (Playwright)

```bash
# Install Playwright browsers (first time)
npx playwright install --with-deps

# Run all E2E tests
npm run test:e2e

# Or via Makefile (starts Docker services first)
make test:e2e

# Run a specific test file
npx playwright test tests/e2e/auth.spec.ts

# Run in a specific browser
npx playwright test --project=chromium
```

E2E tests run against `http://localhost:3000` and cover:
- Authentication flows (login, logout, 2FA)
- Role-based access control (RBAC)
- Tenant isolation verification
- Student CRUD operations
- Attendance tracking
- Financial operations
- Badge system

---

## Code Quality

### ESLint (Frontend)

```bash
npm run lint
```

Configuration is in `eslint.config.js` (flat config format). Key rules:
- `@typescript-eslint/no-unused-vars`: warn (variables prefixed with `_` are ignored)
- `@typescript-eslint/no-explicit-any`: warn
- `no-console`: warn (console.warn and console.error are allowed)
- `react-hooks/rules-of-hooks`: error
- `react-refresh/only-export-components`: warn

### Ruff (Backend)

Ruff replaces both flake8 and isort for Python linting and formatting:

```bash
cd backend

# Lint all files
ruff check .

# Auto-fix linting issues
ruff check --fix .

# Format code
ruff format .

# Check formatting without changing files
ruff format --check .
```

Configuration is in `backend/pyproject.toml`. Key settings:
- **Target:** Python 3.11
- **Line length:** 120 characters
- **Enabled rules:** pycodestyle (E/W), Pyflakes (F), isort (I), pep8-naming (N), pyupgrade (UP), flake8-bugbear (B), flake8-simplify (SIM), flake8-bandit (S), and more
- **Security:** Bandit rules (S) are enabled to catch common vulnerabilities

### Type Checking

**Frontend (TypeScript):**

```bash
npm run type-check
```

**Backend (mypy):**

```bash
cd backend
mypy app/
```

Configuration is in `backend/pyproject.toml`. The project uses gradual type adoption — `disallow_untyped_defs` is currently `false` but `disallow_incomplete_defs` is `true`.

### Pre-Commit Hooks

We recommend setting up pre-commit hooks to catch issues before pushing:

```bash
# Install pre-commit
pip install pre-commit

# Set up hooks
pre-commit install
```

Create a `.pre-commit-config.yaml` at the project root:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-eslint
    rev: v9.0.0
    hooks:
      - id: eslint
        files: \.[jt]sx?$
        types: [file]
```

---

## Security Guidelines

Security is paramount in a multi-tenant SaaS platform handling student data. All contributors must follow these guidelines:

### Never Commit Secrets

- **Never** commit passwords, API keys, JWT secrets, or any credentials to the repository
- Use `.env` files for local configuration (already in `.gitignore`)
- Use Docker Secrets (`/run/secrets/`) in production
- The `SECRET_KEY` validator in `backend/app/core/config.py` will refuse to start in production if the key is less than 32 characters

### Environment Variables

- All secrets are read via `get_secret()` in `backend/app/core/config.py`, which checks Docker Secrets first, then environment variables
- Copy `.env.example` (frontend) or `backend/.env.example` (backend) as templates
- For Docker, copy `.env.docker.example` to `.env.docker`
- Generate strong secrets with: `openssl rand -hex 32`

### OWASP Top 10 Awareness

Be aware of and guard against the OWASP Top 10 vulnerabilities:

| OWASP Category | Mitigation in Guinée Academy |
|---------------|------------------------------|
| **A01 - Broken Access Control** | Role-based permissions via `require_permission()`, RLS enforcement, tenant isolation |
| **A02 - Cryptographic Failures** | bcrypt password hashing, HS256 JWT with 32+ char secrets, HTTPS in production |
| **A03 - Injection** | SQLAlchemy ORM (parameterized queries), Pydantic input validation, DOMPurify on frontend |
| **A04 - Insecure Design** | Multi-layer tenant isolation (JWT + middleware + RLS), quota enforcement |
| **A05 - Security Misconfiguration** | Security headers middleware (HSTS, CSP, X-Frame-Options), debug mode off in production |
| **A07 - Auth Failures** | Rate limiting (100/min default), MFA support, token versioning for logout-all |

### Tenant Isolation

- **Never** bypass tenant isolation — all queries go through `get_db()` which sets the RLS context
- The `TenantMiddleware` extracts `tenant_id` from JWT claims and sets `app.current_tenant_id` for PostgreSQL RLS
- Only `SUPER_ADMIN` can access cross-tenant data via the `X-Tenant-ID` header
- RLS context is always reset on new database sessions to prevent connection pool leaks

### Input Validation

- All API inputs are validated using **Pydantic v2** schemas with strict type checking
- Frontend forms use **Zod** schemas for client-side validation (see `src/lib/schemas/`)
- File uploads are validated for type and size via the storage service
- SQL injection is prevented by using SQLAlchemy ORM — never use raw string interpolation in queries

---

## Internationalization

Guinée Academy supports **5 languages**: French (FR), English (EN), Spanish (ES), Arabic (AR), and Chinese (ZH).

### Translation File Structure

```
src/i18n/
├── config.ts          # i18next initialization
└── locales/
    ├── fr.json        # French (fallback language)
    ├── en.json        # English
    ├── es.json        # Spanish
    ├── ar.json        # Arabic (RTL)
    └── zh.json        # Chinese

src/lib/i18n/
├── index.ts           # Alternative i18n setup
└── locales/
    ├── fr.json
    ├── en.json
    ├── es.json
    ├── ar.json
    └── zh.json
```

### Key Naming Conventions

Use dot-separated, hierarchical keys organized by feature:

```json
{
  "students": {
    "title": "Students",
    "list": {
      "empty": "No students found",
      "search": "Search students..."
    },
    "form": {
      "firstName": "First Name",
      "lastName": "Last Name",
      "dateOfBirth": "Date of Birth"
    },
    "actions": {
      "create": "Add Student",
      "edit": "Edit Student",
      "delete": "Delete Student"
    }
  }
}
```

**Rules:**
- Top-level keys correspond to feature areas (e.g., `students`, `grades`, `settings`)
- Never use flat keys like `"studentListEmpty"` — always nest under the feature
- Common/shared keys go under `"common"`: `common.save`, `common.cancel`, `common.delete`, `common.loading`
- Error messages go under `"errors"`: `errors.unauthorized`, `errors.notFound`

### Adding a New Language

1. **Create the locale file** in `src/i18n/locales/` — copy `en.json` as a starting point
2. **Register the language** in `src/i18n/config.ts`:

```typescript
import de from './locales/de.json';

i18n.init({
  resources: {
    // ...existing languages
    de: { translation: de },
  },
});
```

3. **Translate all keys** in the new locale file — do not leave English placeholders
4. **Test RTL layout** if the language is right-to-left (Arabic is already supported as RTL)
5. **Verify** by switching the language in the app's settings panel

### Using Translations in Code

```tsx
import { useTranslation } from "react-i18next";

function StudentHeader() {
  const { t } = useTranslation();
  return <h1>{t("students.title")}</h1>;
}
```

Never hardcode user-facing strings. Always use `t("key")` and add the key to all locale files.

---

## Release Process

### Versioning

Guinée Academy follows [Semantic Versioning](https://semver.org/) (semver):

- **MAJOR** (`X.0.0`): Breaking API changes, incompatible schema changes
- **MINOR** (`0.X.0`): New features, new API endpoints, backward-compatible
- **PATCH** (`0.0.X`): Bug fixes, security patches, documentation updates

### Changelog

We maintain a `CHANGELOG.md` following the [Keep a Changelog](https://keepachangelog.com/) format. Each release includes sections for:

- **Added**: New features
- **Changed**: Changes to existing functionality
- **Deprecated**: Features to be removed in future releases
- **Removed**: Features removed in this release
- **Fixed**: Bug fixes
- **Security**: Security vulnerability fixes

### Release Steps

1. **Update the version** in `package.json` and `backend/app/core/config.py`
2. **Update `CHANGELOG.md`** with all changes since the last release
3. **Run the full test suite:**

```bash
make frontend     # lint, type-check, test, build
make backend      # install, pytest
make test:e2e     # Playwright E2E tests
```

4. **Create a git tag:**

```bash
git tag -a v1.2.0 -m "Release v1.2.0: Student bulk import and grade analytics"
git push origin v1.2.0
```

5. **Create a GitHub Release** from the tag with the changelog entry
6. **Deploy** via the CI/CD pipeline (Render.com auto-deploys from the release tag)

### CI/CD Pipeline

The GitHub Actions CI pipeline runs on every push and PR:

1. **Preflight**: Merge conflict detection
2. **Frontend**: ESLint → TypeScript type-check → Vitest unit tests → Production build
3. **Backend**: pip install → pytest with containerized PostgreSQL
4. **Docker**: Docker Compose validation → Image build

All checks must pass before a PR can be merged.
