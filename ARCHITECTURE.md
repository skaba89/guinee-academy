# Guinée Academy — Architecture Document

This document provides a comprehensive overview of Guinée Academy's architecture, design decisions, and technical implementation details. It is intended for both new contributors seeking context and senior architects evaluating the system design.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Technology Stack](#technology-stack)
3. [Frontend Architecture](#frontend-architecture)
4. [Backend Architecture](#backend-architecture)
5. [Data Model](#data-model)
6. [Authentication & Authorization](#authentication--authorization)
7. [Multi-Tenancy](#multi-tenancy)
8. [API Design](#api-design)
9. [Infrastructure](#infrastructure)
10. [Security Architecture](#security-architecture)
11. [Performance](#performance)
12. [Scalability](#scalability)

---

## System Overview

Guinée Academy is a **multi-tenant SaaS school management platform** designed for private, public, and institutional schools. The system serves a diverse set of users — administrators, teachers, students, parents, alumni, department heads, accountants, and staff — each with distinct permissions and workflows.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Client Layer                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Web Browser │  │  PWA (iOS)  │  │ PWA (Android)│  │   Mobile App │ │
│  │  React SPA   │  │ Capacitor   │  │  Capacitor   │  │  Capacitor   │ │
│  └──────┬───────┘  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘ │
└─────────┼──────────────────┼──────────────────┼──────────────────┼──────┘
          │                  │                  │                  │
          └──────────────────┴──────────────────┴──────────────────┘
                                     │
                          HTTPS / WSS (API + Realtime)
                                     │
┌────────────────────────────────────┼─────────────────────────────────────┐
│                          API Gateway Layer                               │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Nginx (Docker) / Render Proxy                                  │   │
│  │  • SSL termination  • /api/ → FastAPI  • / → React SPA          │   │
│  └────────────────────────────┬─────────────────────────────────────┘   │
└───────────────────────────────┼─────────────────────────────────────────┘
                                │
┌───────────────────────────────┼─────────────────────────────────────────┐
│                     Application Layer (FastAPI)                          │
│                               │                                         │
│  ┌────────────┐  ┌────────────┴────────────┐  ┌──────────────────┐    │
│  │ Middleware  │  │     API Endpoints       │  │   Services       │    │
│  │ Stack      │  │  • Core (auth, users,   │  │  • Notifications │    │
│  │ • CORS     │  │    tenants, billing)     │  │  • Payment GW    │    │
│  │ • Rate Lim │  │  • Academic (students,  │  │  • Groq AI       │    │
│  │ • Tenant   │  │    grades, attendance)  │  │  • Realtime      │    │
│  │ • Metrics  │  │  • Finance (payments)   │  └──────────────────┘    │
│  │ • Quota    │  │  • Operational (HR,     │                           │
│  │ • Req ID   │  │    admissions, library) │                           │
│  │ • Security │  │                         │                           │
│  │  Headers   │  │                         │                           │
│  └────────────┘  └────────────┬────────────┘                           │
│                               │                                         │
│  ┌────────────┐  ┌────────────┴────────────┐  ┌──────────────────┐    │
│  │  Pydantic   │  │  SQLAlchemy 2.0 ORM    │  │  Alembic         │    │
│  │  Schemas    │  │  • 38 Models            │  │  Migrations      │    │
│  │  (valid.)   │  │  • UUID PKs             │  │                  │    │
│  └────────────┘  └────────────┬────────────┘  └──────────────────┘    │
└───────────────────────────────┼─────────────────────────────────────────┘
                                │
┌───────────────────────────────┼─────────────────────────────────────────┐
│                        Data Layer                                        │
│           ┌───────────────────┼───────────────────┐                     │
│           │                   │                   │                     │
│  ┌────────┴────────┐ ┌───────┴────────┐ ┌────────┴────────┐           │
│  │   PostgreSQL 16  │ │   Redis 7      │ │   MinIO (S3)    │           │
│  │  • RLS policies  │ │  • Cache       │ │  • File uploads │           │
│  │  • 38 tables     │ │  • Rate limit  │ │  • Avatars      │           │
│  │  • UUID PKs      │ │  • Sessions    │ │  • Documents    │           │
│  │  • JSON settings │ │  • Realtime    │ │  • Signatures   │           │
│  └─────────────────┘ └────────────────┘ └─────────────────┘           │
└────────────────────────────────────────────────────────────────────────┘
```

### Multi-Tenant SaaS Model

Guinée Academy implements a **shared database, shared schema** multi-tenancy model with PostgreSQL Row Level Security (RLS) as the primary isolation mechanism. Each school (tenant) shares the same database and tables, but RLS policies ensure complete data isolation at the database level. This model provides the best balance of cost efficiency, operational simplicity, and data security for a SaaS platform.

Key aspects of the multi-tenant model:
- **Tenant identification**: Every authenticated request carries a `tenant_id` in the JWT payload
- **Database-level isolation**: PostgreSQL RLS policies filter all queries by `app.current_tenant_id`
- **Application-level enforcement**: Middleware sets the RLS context before any query executes
- **Cross-tenant access**: Only `SUPER_ADMIN` users can access data across tenants via the `X-Tenant-ID` header
- **Plan-based feature gating**: Each tenant has a subscription plan (starter/pro/enterprise) that gates access to premium features

---

## Technology Stack

### Frontend

| Technology | Version | Rationale |
|-----------|---------|-----------|
| **React** | 18.3.x | Industry-standard UI library with concurrent rendering, suspense, and a vast ecosystem |
| **TypeScript** | 5.8.x | Static type safety, improved DX, catches bugs at compile time |
| **Vite** | 5.4.x | Fast HMR, optimized builds with SWC plugin, native ESM support |
| **Tailwind CSS** | 3.4.x | Utility-first CSS for rapid, consistent UI development with dark mode support |
| **shadcn/ui** | Latest | Accessible, composable UI primitives built on Radix UI — not a dependency, you own the code |
| **TanStack React Query** | 5.83.x | Server state management with caching, background refetch, and optimistic updates |
| **Zustand** | 5.0.x | Lightweight client state management — simpler than Redux, no boilerplate |
| **react-i18next** | 16.5.x | Internationalization with 5 language support (FR, EN, ES, AR, ZH) |
| **React Router DOM** | 6.30.x | Declarative routing with nested layouts and route guards |
| **Zod** | 3.25.x | Runtime type validation for forms and API responses |
| **Axios** | 1.13.x | HTTP client with interceptors for auth token injection and refresh |
| **Recharts** | 2.15.x | Composable charting library for dashboard visualizations |
| **Framer Motion** | 12.x | Animation library for page transitions and micro-interactions |
| **Capacitor** | 8.0.x | Native mobile app compilation (iOS/Android) from the same web codebase |
| **Dexie** | 4.3.x | IndexedDB wrapper for offline-first data persistence |
| **Vite PWA Plugin** | 1.2.x | Service worker generation for Progressive Web App support |

### Backend

| Technology | Version | Rationale |
|-----------|---------|-----------|
| **FastAPI** | 0.104–0.115 | High-performance async Python framework with automatic OpenAPI docs, dependency injection, and Pydantic integration |
| **Python** | 3.11+ | Performance improvements, exception groups, modern syntax |
| **SQLAlchemy** | 2.0.x | Modern ORM with typed queries, async support, and advanced relationship handling |
| **psycopg** | 3.2.x | PostgreSQL adapter v3 with native async support (replaces psycopg2) |
| **Alembic** | 1.13.x | Database migration engine with autogenerate and branching support |
| **Pydantic** | 2.5.x | Data validation and settings management with v2 performance improvements |
| **PyJWT** | 2.8.x | JWT token creation and verification (HS256 signing) |
| **Passlib + bcrypt** | 1.7.x / 4.2.x | Secure password hashing with bcrypt algorithm |
| **Redis** | 5.0.x (client) | Caching, rate limiting state, real-time pub/sub, session token versioning |
| **MinIO** | 7.2.x (client) | S3-compatible object storage for file uploads, avatars, documents, and signatures |
| **Stripe** | 8.0.x | Subscription billing, payment processing, and webhook handling |
| **SlowAPI** | 0.1.x | Rate limiting middleware for FastAPI (100 requests/minute default) |
| **Sentry SDK** | 2.0.x | Error tracking, performance monitoring, and structured logging |
| **Prometheus Client** | 0.20.x | Application metrics exposition (request count, duration, active connections) |
| **Groq** | 0.11.x | AI chat integration using LLaMA 3.3 70B model |

### Infrastructure

| Technology | Version | Rationale |
|-----------|---------|-----------|
| **PostgreSQL** | 16 | RLS support, JSON columns, UUID native type, robust replication |
| **Redis** | 7 | In-memory caching, pub/sub, rate limiting state store |
| **MinIO** | RELEASE.2024-11-07 | Self-hosted S3-compatible storage, no vendor lock-in |
| **Docker Compose** | v2 | Local development environment parity with production |
| **Nginx** | Latest | Reverse proxy, SSL termination, static file serving |
| **Render.com** | — | Managed deployment with auto-scaling, managed PostgreSQL and Redis |
| **GitHub Actions** | — | CI/CD pipeline for linting, testing, and deployment |

---

## Frontend Architecture

### React Component Hierarchy

The frontend follows a layered component architecture with clear separation of concerns:

```
App.tsx
├── AuthContext Provider
│   └── TenantContext Provider
│       └── ThemeContext Provider
│           └── QueryClientProvider (React Query)
│               └── I18nextProvider
│                   └── Router (React Router v6)
│                       ├── PublicRoutes (/auth, /bootstrap, /change-password)
│                       ├── ProtectedRoute + AdminLayout → AdminRoutes
│                       ├── ProtectedRoute + TeacherLayout → TeacherRoutes
│                       ├── ProtectedRoute + StudentLayout → StudentRoutes
│                       ├── ProtectedRoute + ParentLayout → ParentRoutes
│                       ├── ProtectedRoute + DepartmentLayout → DepartmentRoutes
│                       ├── ProtectedRoute + AlumniLayout → AlumniRoutes
│                       └── ProtectedRoute + SuperAdminLayout → SuperAdminRoutes
```

### Routing (152 Pages)

Routes are organized by user role in `src/routes/`:

| Route File | Layout | Key Pages |
|-----------|--------|-----------|
| `AdminRoutes.tsx` | `AdminLayout` | Dashboard, Students, Grades, Attendance, Finance, HR, Settings, Analytics |
| `TeacherRoutes.tsx` | `TeacherLayout` | Dashboard, My Classes, Grades Entry, Attendance, Schedule |
| `StudentRoutes.tsx` | `StudentLayout` | Dashboard, My Grades, My Schedule, Badges, Homework |
| `ParentRoutes.tsx` | `ParentLayout` | Dashboard, Children, Analytics, Invoices, Messages |
| `DepartmentRoutes.tsx` | `DepartmentLayout` | Dashboard, Teachers, Students, Schedule, Exams |
| `AlumniRoutes.tsx` | `AlumniLayout` | Dashboard, Profile, Events |
| `PublicRoutes.tsx` | None | Auth, Bootstrap, Change Password |

Each layout component provides:
- **Responsive sidebar** (`ResponsiveSidebar.tsx`) with role-specific navigation
- **Mobile bottom navigation** (`MobileBottomNav.tsx`) for touch devices
- **Page transitions** (`PageTransition.tsx`) using Framer Motion
- **Tenant switcher** (`TenantSwitcher.tsx`) for SUPER_ADMIN cross-tenant access
- **Notification center** (`NotificationCenter.tsx`) with real-time updates

### State Management

The project uses a **layered state management** strategy with clear boundaries:

**Server State (TanStack React Query v5):**

All API data flows through React Query hooks defined in `src/queries/`. This handles caching, background refetching, pagination, and optimistic updates:

```tsx
// src/queries/students.ts
export function useStudents(page: number, search: string) {
  return useQuery({
    queryKey: ["students", page, search],
    queryFn: () => apiClient.get("/students", { params: { page, search } }),
    staleTime: 30_000, // 30 seconds
  });
}
```

Query keys are centralized in `src/lib/queryKeys.ts` to prevent duplication and enable targeted cache invalidation.

**Client State (Zustand v5):**

Zustand manages pure UI state that does not come from the API:
- Sidebar open/closed state
- Command palette visibility
- Theme preferences
- Onboarding tour progress

**Auth and Tenant State (React Context):**

Three context providers manage authentication, tenant, and theme state across the entire application:
- `AuthContext` — JWT token, user profile, roles, permission checks
- `TenantContext` — Current tenant, tenant settings, branding
- `ThemeContext` — Dark/light mode, dynamic theming from tenant settings

### i18n Strategy

The application supports 5 languages using `i18next` with browser language detection:

- **Default/Fallback:** French (FR)
- **Supported:** English (EN), Spanish (ES), Arabic (AR, RTL), Chinese (ZH)
- **Detection order:** `localStorage` → `navigator` language
- **Storage:** Language preference persisted in `localStorage` under key `i18nextLng`
- **RTL support:** Arabic uses right-to-left layout with automatic direction switching

Translation files are located at `src/i18n/locales/{lang}.json` with a secondary set at `src/lib/i18n/locales/{lang}.json`.

### UI Component Library (shadcn/ui)

The project uses **shadcn/ui** — a collection of accessible, composable React components built on top of Radix UI primitives. Unlike traditional component libraries, shadcn/ui components are **copied into the project** (in `src/components/ui/`) rather than installed as a dependency. This gives full control over styling and behavior.

Key components include:
- `DataTable.tsx` — Generic data table with sorting, filtering, and pagination
- `Dialog.tsx` / `Sheet.tsx` — Modal and slide-over panels
- `Form.tsx` — React Hook Form integration with Zod validation
- `Command.tsx` — Command palette (cmdk) for global search and actions
- `PlanGate.tsx` — Feature gate component that checks tenant subscription plan before rendering

---

## Backend Architecture

### FastAPI Application Structure

The backend follows a clean, layered architecture:

```
backend/app/
├── main.py                 # Application factory, middleware stack, lifespan events
├── core/                   # Cross-cutting concerns
│   ├── config.py           # Pydantic Settings (all env vars, validation)
│   ├── database.py         # SQLAlchemy engine, SessionLocal, RLS context
│   ├── security.py         # JWT, password hashing, role permissions, plan gating
│   ├── cache.py            # Redis async client with sfp: key prefix
│   ├── storage.py          # MinIO S3 client for file operations
│   ├── exceptions.py       # Structured error hierarchy and handlers
│   ├── events.py           # FastAPI lifespan (startup/shutdown)
│   └── logging_config.py   # Structured logging setup
├── api/v1/                 # API version 1
│   ├── router.py           # Central router assembling all sub-routers
│   └── endpoints/          # Endpoint modules by domain
│       ├── core/           # Auth, Users, Tenants, Health, Billing, MFA, AI, Storage, etc.
│       ├── academic/       # Students, Grades, Attendance, Subjects, Levels, etc.
│       ├── finance/        # Payments, Payment Schedules
│       └── operational/    # HR, School Life, Admissions, Schedule, Library, etc.
├── models/                 # SQLAlchemy ORM models
├── schemas/                # Pydantic request/response schemas
├── crud/                   # Database query helper functions
├── middlewares/            # ASGI middleware classes
├── services/               # Business logic services
└── utils/                  # Utility functions
```

### Middleware Stack

The FastAPI middleware stack executes in **reverse registration order** (last registered = first executed). The following middlewares are registered in `app/main.py`:

| Middleware | Registration Order | Execution Order | Purpose |
|-----------|-------------------|----------------|---------|
| `CORSMiddleware` | 1st | 6th (outermost) | Cross-origin request handling |
| `SlowAPIMiddleware` | 2nd | 5th | Rate limiting (100 req/min default) |
| `QuotaMiddleware` | 3rd | 4th | Per-tenant resource quota enforcement |
| `TenantMiddleware` | 4th | 3rd | Tenant identification and RLS context setup |
| `token_version_middleware` | 5th (function) | 2nd | JWT token version validation (logout-all enforcement) |
| `security_headers_middleware` | 6th (function) | 1st (innermost) | Security headers (HSTS, CSP, X-Frame-Options) |
| `RequestIDMiddleware` | — | — | X-Request-ID propagation |
| `MetricsMiddleware` | — | — | Prometheus metrics collection |

**Middleware execution flow:**

```
Request → CORS → Rate Limit → Quota Check → Tenant Isolation → Token Version → Security Headers → Endpoint
```

### Dependency Injection

FastAPI's dependency injection system is used extensively for cross-cutting concerns:

```python
# Database session with RLS context
db: Session = Depends(get_db)

# Current authenticated user (JWT payload)
current_user: dict = Depends(get_current_user)

# Permission-based authorization
current_user: dict = Depends(require_permission("students:read"))

# Plan-based feature gating
current_user: dict = Depends(require_plan("pro"))
```

The `get_db()` dependency automatically:
1. Creates a new SQLAlchemy session
2. Resets the RLS context (`app.current_tenant_id = NULL`) to prevent connection pool leaks
3. Sets the RLS context to the current tenant from `tenant_context` ContextVar
4. Verifies the database connection is alive (`SELECT 1`)
5. Yields the session for the endpoint
6. Closes the session in the `finally` block

---

## Data Model

### Entity Relationship Overview

Guinée Academy has **38 SQLAlchemy models** organized across several domains. The following diagram describes the key entity relationships:

```
Tenant (1) ────────────→ (N) User
    │                         │
    ├─→ (N) Campus            ├─→ (N) UserRole
    ├─→ (N) Level             └─→ (1) Profile
    ├─→ (N) Subject               │
    ├─→ (N) Department            └─→ (N) ParentStudent ──→ Student
    ├─→ (N) AcademicYear               │
    ├─→ (N) Term                        ├─→ (N) Enrollment ──→ Classroom
    ├─→ (N) Classroom                   ├─→ (N) Grade ──→ Assessment
    ├─→ (N) Student                     ├─→ (N) Attendance
    ├─→ (N) Payment/Invoice             ├─→ (N) StudentCheckIn
    ├─→ (N) Employee                    └─→ (N) AdmissionApplication
    ├─→ (N) Contract                │
    ├─→ (N) LeaveRequest            Employee ──→ Contract
    ├─→ (N) Payslip                           ──→ LeaveRequest
    ├─→ (N) Notification                      ──→ Payslip
    ├─→ (N) SchoolEvent
    ├─→ (N) ScheduleSlot
    ├─→ (N) AuditLog
    ├─→ (N) PublicPage
    ├─→ (N) Room
    └─→ (N) TenantSecuritySettings
```

### Key Relationships

| Parent | Child | Relationship | Description |
|--------|-------|-------------|-------------|
| Tenant | User | One-to-Many | All users belong to a tenant |
| Tenant | Student | One-to-Many | All students belong to a tenant |
| Tenant | Campus | One-to-Many | A school may have multiple campuses |
| User | UserRole | One-to-Many | A user can have multiple roles |
| Student | Enrollment | One-to-Many | A student can be enrolled in multiple classes/years |
| Student | Grade | One-to-Many | A student receives grades for assessments |
| Student | Attendance | One-to-Many | Daily attendance records per student |
| Classroom | Enrollment | One-to-Many | A classroom has many enrolled students |
| Employee | Contract | One-to-Many | An employee can have multiple employment contracts |
| Employee | LeaveRequest | One-to-Many | An employee submits leave requests |
| Assessment | Grade | One-to-Many | An assessment receives grades from multiple students |

### Base Model Mixins

All models inherit from a set of reusable mixins defined in `backend/app/models/base.py`:

- **`UUIDMixin`**: Provides a UUID primary key column (`id`) using a cross-database `GUID` type that maps to PostgreSQL's native `UUID` type and falls back to `CHAR(32)` for SQLite
- **`TimestampMixin`**: Provides `created_at` and `updated_at` columns with auto-populated UTC timestamps
- **`TenantMixin`**: Provides a `tenant_id` foreign key column pointing to `tenants.id` with `CASCADE` delete and an index

### Tenant Isolation Strategy

Data isolation is enforced at **two layers** simultaneously:

1. **Database Level (PostgreSQL RLS)**: Row Level Security policies on every tenant-scoped table ensure that queries can only return rows where `tenant_id` matches the session-level `app.current_tenant_id` setting. This is the authoritative isolation layer — even a bug in the application code cannot leak cross-tenant data if RLS is active.

2. **Application Level (Middleware + ContextVar)**: The `TenantMiddleware` extracts the `tenant_id` from the JWT payload, stores it in a `ContextVar`, and the `get_db()` dependency sets `app.current_tenant_id` via PostgreSQL's `set_config()` function before any query executes.

The RLS context is always **reset to NULL** at the beginning of each database session to prevent connection pool leaks where a connection previously used for tenant A might be reused for tenant B without clearing the context.

---

## Authentication & Authorization

### JWT Authentication Flow

Guinée Academy uses **100% native JWT authentication** (no external identity provider like Keycloak or Auth0):

```
1. Client sends POST /api/v1/auth/login/ { email, password }
2. Backend verifies credentials (bcrypt hash comparison)
3. Backend creates JWT with claims: { sub: user_id, email, roles, tenant_id, tv: token_version }
4. JWT is signed with HS256 using SECRET_KEY (minimum 32 characters)
5. JWT includes issuer ("guinee-academy") and audience ("guinee-academy-api") claims
6. Client stores token in memory/localStorage
7. Client sends token in Authorization: Bearer header on every request
8. Token expires after 30 minutes (configurable via ACCESS_TOKEN_EXPIRE_MINUTES)
9. Client uses POST /api/v1/auth/refresh/ to get a new token before expiry
10. On logout-all, token version is bumped in Redis — all existing tokens are invalidated
```

### Role Hierarchy (11 Roles)

| Role | Level | Description | Key Permissions |
|------|-------|-------------|-----------------|
| **SUPER_ADMIN** | Platform | Full platform access, cross-tenant operations | `*` (all permissions) |
| **TENANT_ADMIN** | Tenant | Full access within their tenant | All except `rgpd:delete`, `tenants:write`, `tenants:delete` |
| **DIRECTOR** | Tenant | School director with broad access | Users, students, grades, attendance, settings, analytics, finance (read), HR |
| **DEPARTMENT_HEAD** | Department | Manages a specific department | Students (read), grades, attendance, subjects, schedule, admissions (read) |
| **TEACHER** | Classroom | Manages own classes | Students (read), grades (read/write), attendance (read/write), subjects (read) |
| **STUDENT** | Self | Access to own data | `me:read`, own grades and attendance |
| **PARENT** | Children | Access to children's data | `me:read`, children's grades and attendance |
| **ALUMNI** | Self | Limited alumni access | Students/grades/attendance (read) |
| **STAFF** | Tenant | Administrative staff | Students (read/write), attendance, admissions |
| **ACCOUNTANT** | Tenant | Financial operations | Finance (read/write), payments, students (read) |
| **SECRETARY** | Tenant | Administrative and enrollment | Students (read/write), attendance, admissions, enrollments, certificates |

### Permission Matrix

Permissions follow a `resource:action` pattern (e.g., `students:read`, `grades:write`). The `require_permission()` dependency enforces these at the endpoint level:

```python
@router.post("/")
async def create_student(
    current_user: dict = Depends(require_permission("students:write")),
    ...
):
```

The wildcard `*` grants all permissions (only SUPER_ADMIN has this). Resource-level wildcards like `students:*` also grant full access to a resource.

### Plan-Based Feature Gating

Beyond role-based permissions, features can be gated by subscription plan:

```python
@router.post("/ai/chat/")
async def chat(
    _plan: None = Depends(require_plan("pro")),
    current_user: dict = Depends(get_current_user),
):
```

Plan hierarchy: `starter` (0) < `pro` (1) < `enterprise` (2). SUPER_ADMIN always bypasses plan checks. If a tenant's subscription is expired or below the required plan, the API returns HTTP 402 with an upgrade prompt.

---

## Multi-Tenancy

### Tenant Isolation Strategy

Guinée Academy implements **defense-in-depth** tenant isolation:

```
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 1: JWT Claims                                                 │
│   tenant_id embedded in JWT payload → extracted by TenantMiddleware │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 2: Application Middleware                                     │
│   TenantMiddleware sets ContextVar → get_db() applies to session   │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 3: PostgreSQL RLS                                             │
│   set_config('app.current_tenant_id', tenant_id, false)            │
│   RLS policies: USING (tenant_id = current_setting(                 │
│       'app.current_tenant_id')::uuid)                              │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 4: Connection Pool Reset                                      │
│   get_db() always resets RLS context to NULL before setting it     │
│   Prevents cross-tenant leaks from pooled connections              │
└─────────────────────────────────────────────────────────────────────┘
```

### RLS Policies

RLS is enabled on all tenant-scoped tables via Alembic migrations (primarily `20260224_0730_enable_rls.py` and `20260227_2309_enforce_rls_on_all_tables.py`). Each policy follows this pattern:

```sql
ALTER TABLE students ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON students
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

The health check endpoint (`GET /health/`) verifies RLS status by querying `pg_class.relrowsecurity` on the `students` table.

### X-Tenant-ID Header

The `X-Tenant-ID` header is used **only** for SUPER_ADMIN cross-tenant access:

- When a SUPER_ADMIN (who has no `tenant_id` in their JWT) needs to access a specific tenant's data, the frontend sends the target `tenant_id` in the `X-Tenant-ID` header
- The `TenantMiddleware` validates the header value is a proper UUID format
- The `get_current_user()` dependency verifies the referenced tenant actually exists in the database
- For all other users, the `tenant_id` is taken **exclusively** from the JWT payload — the header is ignored to prevent tenant spoofing

### SUPER_ADMIN Cross-Tenant Access

SUPER_ADMIN users are unique in that they may not belong to a specific tenant. The system handles this as follows:

1. SUPER_ADMIN JWT tokens may have `tenant_id = null`
2. When accessing tenant-scoped endpoints, the frontend includes `X-Tenant-ID`
3. The middleware extracts the header value and sets the RLS context
4. SUPER_ADMIN retains full permissions (`*`) regardless of which tenant they are viewing
5. Platform-level endpoints (tenant CRUD, billing overview) do not require a tenant context

---

## API Design

### REST Conventions

The API follows RESTful conventions with consistent patterns:

| Action | HTTP Method | URL Pattern | Example |
|--------|------------|-------------|---------|
| List | `GET` | `/api/v1/students` | List all students (paginated) |
| Get | `GET` | `/api/v1/students/{id}` | Get a specific student |
| Create | `POST` | `/api/v1/students` | Create a new student |
| Update | `PUT`/`PATCH` | `/api/v1/students/{id}` | Update a student |
| Delete | `DELETE` | `/api/v1/students/{id}` | Delete a student |

### API Versioning

All endpoints are versioned under `/api/v1/`. The version prefix is configured via `settings.API_V1_STR` in `backend/app/core/config.py`.

When breaking changes are needed:
1. Create a new `v2` router in `backend/app/api/v2/`
2. Maintain the `v1` router with backward-compatible behavior
3. Deprecate `v1` endpoints with sunset headers
4. Remove `v1` only after all clients have migrated

### Pagination

List endpoints support cursor-based or offset pagination:

```python
@router.get("/")
async def list_students(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
```

Response format:

```json
{
  "items": [...],
  "total": 1500,
  "skip": 0,
  "limit": 100
}
```

### Error Format

All errors follow a consistent structure:

```json
{
  "error": "RESOURCE_NOT_FOUND",
  "message": "Student with ID abc-123 not found",
  "detail": "Student with ID abc-123 not found",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

Error codes are defined in `backend/app/core/exceptions.py` (`ErrorCode` class):

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `RESOURCE_NOT_FOUND` | 404 | Requested resource does not exist |
| `VALIDATION_ERROR` | 422 | Input validation failed |
| `PERMISSION_DENIED` | 403 | User lacks required permission |
| `TENANT_REQUIRED` | 400 | Tenant identification missing |
| `DUPLICATE_ENTRY` | 409 | Resource already exists |
| `RATE_LIMITED` | 429 | Rate limit exceeded |
| `QUOTA_EXCEEDED` | 429 | Tenant quota limit reached |
| `UNAUTHORIZED` | 401 | Authentication required or token invalid |
| `PLAN_REQUIRED` | 402 | Feature requires higher subscription plan |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

### OpenAPI Documentation

Interactive API documentation is available at:
- **Swagger UI**: `http://localhost:8000/docs` (development only, disabled in production)
- **ReDoc**: `http://localhost:8000/redoc`

The documentation is auto-generated from FastAPI endpoint definitions and Pydantic schemas. All endpoints include type annotations, descriptions, and example values.

---

## Infrastructure

### Docker Compose Services

The local development environment uses Docker Compose with the following services:

| Service | Image | Port | Memory Limit | Health Check | Purpose |
|---------|-------|------|-------------|-------------|---------|
| **postgres** | `postgres:16-alpine` | 5432 | 512 MB | `pg_isready` | Primary database with RLS |
| **redis** | `redis:7-alpine` | 6379 | 128 MB | `redis-cli ping` | Cache, rate limiting, sessions |
| **minio** | `minio/minio:RELEASE.2024-11-07` | 9000 (API) / 9001 (Console) | 512 MB | `mc ready local` | S3-compatible file storage |
| **api** | Custom (`backend/Dockerfile.dev`) | 8000 | 512 MB | `urllib.urlopen(/health/)` | FastAPI backend |
| **frontend** | Custom (`Dockerfile`) | 3000 | 128 MB | `wget http://127.0.0.1:80/` | Nginx + React SPA |
| **pgadmin** | `dpage/pgadmin4:8.13` | 5050 | 256 MB | — | Database management UI |
| **db-backup** | `prodrigestivill/postgres-backup-local:16-alpine` | — | — | — | Automated PostgreSQL backups |

All services share a `guinee-academy-network` bridge network. Volumes are used for persistent data (`pg_data`, `redis_data`, `minio_data`) and backups are stored in `./infra/backups`.

### Health Checks

The API health endpoint (`GET /health/`) provides a comprehensive system status:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {
    "database": "connected",
    "cache": "connected",
    "rls": "active"
  }
}
```

- Returns HTTP 200 if healthy, HTTP 503 if degraded
- Checks PostgreSQL connectivity (`SELECT 1`)
- Checks Redis connectivity (`PING`)
- Verifies RLS is enabled on the `students` table (PostgreSQL only)

### Monitoring

**Sentry** provides error tracking and performance monitoring:
- Initialized before the FastAPI app starts
- Integrations: FastAPI, SQLAlchemy, Redis
- Sensitive data (Authorization, X-Tenant-ID, Cookie headers) is scrubbed before sending
- `send_default_pii=False` for RGPD compliance
- Configurable trace sample rate (`SENTRY_TRACES_SAMPLE_RATE`, default 5%)

**Prometheus** provides application metrics:
- `http_requests_total` (Counter) — total requests by method, endpoint, status code
- `http_request_duration_seconds` (Histogram) — request latency distribution
- `active_connections_total` (Gauge) — concurrent connections being processed
- UUID and numeric path segments are normalized to `{id}` to limit label cardinality
- Metrics endpoint at `GET /metrics/` — protected by `METRICS_SECRET` in production

---

## Security Architecture

### Threat Model

| Threat Category | Mitigation |
|----------------|------------|
| **Cross-tenant data access** | PostgreSQL RLS + application-level tenant_id enforcement + middleware validation |
| **Token theft/replay** | HS256 signed JWT with issuer/audience claims, short expiry (30 min), token versioning for logout-all |
| **Brute-force attacks** | Rate limiting (100 req/min via SlowAPI), bcrypt password hashing (cost factor auto) |
| **SQL injection** | SQLAlchemy ORM with parameterized queries, no raw string interpolation |
| **XSS** | React auto-escaping, DOMPurify for user-generated HTML, CSP headers |
| **CSRF** | SameSite cookies, Bearer token authentication (not cookie-based sessions) |
| **Clickjacking** | X-Frame-Options: DENY, CSP frame-ancestors: 'none' |
| **Information disclosure** | Production error messages hide stack traces, Sentry scrubs sensitive headers |
| **Privilege escalation** | Role-based permission checks on every endpoint, no wildcards except SUPER_ADMIN |
| **Tenant quota abuse** | QuotaMiddleware enforces per-tenant resource limits on creation endpoints |

### Security Headers

The `security_headers_middleware` adds the following headers to every API response:

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: frame-ancestors 'none'
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

### Rate Limiting

Rate limiting is enforced via SlowAPI (built on top of `limits` library):

- **Default limit**: 100 requests per minute per client IP
- **Client IP detection**: Respects `X-Forwarded-For` from trusted proxies only (127.0.0.1, ::1, Render internal ranges)
- **Headers**: Rate limit info is exposed in response headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`)
- **Custom limits**: Individual endpoints can override the default with `@limiter.limit("5/minute")`

### Input Validation

- **Backend**: All inputs are validated by Pydantic v2 schemas with strict type checking, min/max length constraints, and regex patterns
- **Frontend**: Forms use React Hook Form + Zod schemas for client-side validation before API calls
- **File uploads**: Validated for MIME type and size by the storage service
- **SQL injection prevention**: All database queries use SQLAlchemy ORM with parameterized bindings — raw string interpolation in SQL is never used

### CORS Policy

CORS is configured via the `CORSMiddleware` with origins from `BACKEND_CORS_ORIGINS` (comma-separated in environment variables). Key security measures:

- Credentials are allowed for specific origins (not `*`)
- CORS headers are added to error responses to ensure the browser can read them
- The `TenantMiddleware` includes CORS headers in its error responses to prevent opaque error blocks

---

## Performance

### Caching Strategy (Redis)

Redis is used as a multi-purpose cache with the `sfp:` key prefix:

| Use Case | Key Pattern | TTL | Description |
|----------|------------|-----|-------------|
| **API response cache** | `sfp:api:{endpoint}:{hash}` | 30–300s | Cached list/detail responses for expensive queries |
| **Token version** | `ga:user_token_version:{user_id}` | None (persistent) | Current token version for logout-all enforcement |
| **Rate limit counters** | `sfp:rate_limit:{ip}` | 60s | SlowAPI rate limit state |
| **Real-time pub/sub** | Channel-based | N/A | WebSocket/SSE event distribution |
| **Session data** | `sfp:session:{session_id}` | 24h | Temporary session-related data |

The `RedisClient` class in `backend/app/core/cache.py` provides an async interface with automatic SSL/TLS detection based on the URL scheme (`redis://` vs `rediss://`).

### Database Connection Pooling

SQLAlchemy connection pooling is configured in `backend/app/core/database.py`:

```python
pool_size = 10          # Persistent connections per worker
max_overflow = 20       # Additional connections during spikes (total: 30 per worker)
pool_pre_ping = True    # Verify connections before use (handles dropped connections)
```

For multi-worker deployments (Render Standard with 2+ dynos), these values should be reduced to stay under PostgreSQL's connection limit:
- `DATABASE_POOL_SIZE=5`, `DATABASE_MAX_OVERFLOW=10` per worker

### Frontend Optimizations

- **Code splitting**: React lazy loading for route-level components reduces initial bundle size
- **Virtual scrolling**: `@tanstack/react-virtual` for large data tables (e.g., student lists with 1000+ rows)
- **Optimistic updates**: React Query mutations update the UI before the server responds
- **Offline support**: Dexie (IndexedDB) for offline data persistence, service worker for PWA
- **Image optimization**: `src/lib/imageCompression.ts` for client-side image compression before upload
- **Debounced search**: `useDebounce` hook prevents excessive API calls during typing
- **Intersection observer**: `useIntersectionObserver` for lazy loading components on scroll

---

## Scalability

### Horizontal Scaling

The FastAPI backend is designed for **stateless horizontal scaling**:

- No server-side sessions — all state is in JWT tokens and Redis
- Database connections are pooled per worker with configurable pool sizes
- File storage is offloaded to MinIO (S3-compatible), not local disk
- Rate limiting state is shared via Redis across all API instances

**Scaling strategy:**

```
                    ┌──────────────┐
                    │ Load Balancer │
                    └──────┬───────┘
               ┌───────────┼───────────┐
               │           │           │
         ┌─────┴─────┐ ┌──┴──────┐ ┌──┴──────┐
         │  API Worker │ │ API Worker │ │ API Worker │
         │  (Uvicorn)  │ │ (Uvicorn)  │ │ (Uvicorn)  │
         └─────┬───────┘ └────┬──────┘ └────┬──────┘
               │               │              │
               └───────────────┼──────────────┘
                               │
                    ┌──────────┴──────────┐
                    │   PostgreSQL 16      │
                    │   (Managed/RDS)      │
                    └──────────┬──────────┘
                               │
                    ┌──────────┴──────────┐
                    │   Redis 7            │
                    │   (Managed/ElastiCache)│
                    └─────────────────────┘
```

### Database Connection Pooling

When scaling to multiple API workers:
1. Each worker maintains its own SQLAlchemy connection pool
2. Total connections = `workers × (pool_size + max_overflow)`
3. Stay under PostgreSQL's `max_connections` (default 97 on Render managed PostgreSQL)
4. Reduce `DATABASE_POOL_SIZE` and `DATABASE_MAX_OVERFLOW` per worker when adding workers

### Redis Clustering

For high-availability deployments:
- Redis can be deployed as a cluster with primary/replica topology
- The `RedisClient` supports `rediss://` URLs for TLS connections
- Managed Redis services (Render Redis, Upstash, AWS ElastiCache) handle clustering transparently

### Stateless API Design

Every API request is self-contained:
- **Authentication**: JWT in Authorization header (not cookies)
- **Tenant context**: JWT claim + X-Tenant-ID header (not server-side sessions)
- **Request tracking**: X-Request-ID header (generated by middleware if absent)
- **File storage**: MinIO/S3 (not local filesystem)
- **Rate limiting**: Redis-backed (shared across instances)
- **Token invalidation**: Redis token version (shared across instances)

This stateless design means any API instance can handle any request, enabling true horizontal scaling with no session affinity requirements.
