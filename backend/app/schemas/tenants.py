from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TenantBase(BaseModel):
    name: str
    slug: str
    type: str
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    website: str | None = None


class TenantCreate(TenantBase):
    country: str | None = "GN"
    currency: str | None = "GNF"
    academic_year_start: datetime | None = None
    academic_year_end: datetime | None = None
    levels: list[str] | None = None
    terms: list[dict[str, Any]] | None = None


class TenantUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    website: str | None = None
    is_active: bool | None = None
    settings: dict[str, Any] | None = None


class TenantResponse(TenantBase):
    id: UUID
    currency: str | None = None
    created_at: datetime
    updated_at: datetime
    is_active: bool
    settings: dict[str, Any] | None = {}
    # Extra fields for super admin views
    student_count: int | None = None
    user_count: int | None = None

    model_config = ConfigDict(from_attributes=True)


class TenantWithAdminCreate(BaseModel):
    """Schema for creating a tenant along with its first admin user (SUPER_ADMIN only)."""
    # Tenant fields
    name: str
    slug: str
    type: str
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    website: str | None = None
    country: str | None = "GN"
    currency: str | None = "GNF"
    levels: list[str] | None = None
    # Admin user fields
    admin_email: str
    admin_first_name: str
    admin_last_name: str
    admin_password: str


class TenantAdminUserCreate(BaseModel):
    """Schema for creating an admin user for an existing tenant (SUPER_ADMIN only)."""
    email: str
    first_name: str
    last_name: str
    password: str
    role: str = "TENANT_ADMIN"


class TenantLandingAnnouncement(BaseModel):
    """A single announcement shown on the tenant landing page."""
    title: str
    body: str
    date: str | None = None
    is_pinned: bool = False
    category: str | None = None


class TenantLandingSettings(BaseModel):
    """Structured landing page settings stored inside Tenant.settings['landing']."""
    logo_url: str | None = None
    banner_url: str | None = None
    description: str | None = None
    primary_color: str = "#1e3a5f"
    secondary_color: str | None = None
    custom_domain: str | None = None
    show_stats: bool = True
    show_programs: bool = True
    gallery: list[str] = []
    announcements: list[TenantLandingAnnouncement] = []
    contact_email: str | None = None
    contact_phone: str | None = None
    facebook_url: str | None = None
    twitter_url: str | None = None
    linkedin_url: str | None = None


class TenantPublicCard(BaseModel):
    """Lightweight tenant representation used in public directory listings."""
    id: UUID
    name: str
    slug: str
    type: str
    address: str | None = None
    email: str | None = None
    website: str | None = None
    logo_url: str | None = None
    description: str | None = None
    primary_color: str = "#1e3a5f"

    model_config = ConfigDict(from_attributes=True)


class TenantPublicStats(BaseModel):
    """Aggregate statistics shown on a tenant landing page."""
    student_count: int = 0
    teacher_count: int = 0


class TenantPublicResponse(BaseModel):
    """Full public data for a tenant landing page."""
    id: UUID
    name: str
    slug: str
    type: str
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    website: str | None = None
    is_active: bool
    landing: TenantLandingSettings
    stats: TenantPublicStats
    programs: list[Any] = []
    departments: list[Any] = []
    announcements: list[TenantLandingAnnouncement] = []

    model_config = ConfigDict(from_attributes=True)
