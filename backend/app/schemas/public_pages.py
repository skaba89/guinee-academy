"""Pydantic schemas for public pages."""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


# ─── Enums / Constants ────────────────────────────────────────────────

VALID_PAGE_TYPES = {
    "ADMISSION", "PROGRAMS", "RESEARCH", "CAMPUS", "CONTACT", "ABOUT", "CUSTOM", "HOME",
}


# ─── Request schemas ──────────────────────────────────────────────────

class PublicPageCreate(BaseModel):
    """Schema for creating a new public page."""
    title: str
    slug: str
    page_type: str = "CUSTOM"
    content: dict[str, Any] | None = None
    template: str | None = "default"
    primary_color: str | None = None
    secondary_color: str | None = None
    is_published: bool = False
    sort_order: int = 0
    meta_title: str | None = None
    meta_description: str | None = None
    show_in_nav: bool = True
    nav_label: str | None = None

    @field_validator("page_type")
    @classmethod
    def validate_page_type(cls, v: str) -> str:
        v_upper = v.upper()
        if v_upper not in VALID_PAGE_TYPES:
            raise ValueError(f"Invalid page_type. Must be one of: {', '.join(sorted(VALID_PAGE_TYPES))}")
        return v_upper

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        # Allow lowercase alphanumeric, hyphens, and underscores
        slug = v.strip().lower()
        if not slug:
            raise ValueError("Slug cannot be empty")
        return slug

    @field_validator("primary_color", "secondary_color", mode="before")
    @classmethod
    def validate_color(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v.startswith("#") or len(v) != 7:
            raise ValueError("Color must be a valid hex string, e.g. '#1e3a5f'")
        return v


class PublicPageUpdate(BaseModel):
    """Schema for updating an existing public page (all fields optional)."""
    title: str | None = None
    slug: str | None = None
    page_type: str | None = None
    content: dict[str, Any] | None = None
    template: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    is_published: bool | None = None
    sort_order: int | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    show_in_nav: bool | None = None
    nav_label: str | None = None

    @field_validator("page_type")
    @classmethod
    def validate_page_type(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v_upper = v.upper()
        if v_upper not in VALID_PAGE_TYPES:
            raise ValueError(f"Invalid page_type. Must be one of: {', '.join(sorted(VALID_PAGE_TYPES))}")
        return v_upper

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str | None) -> str | None:
        if v is None:
            return None
        slug = v.strip().lower()
        if not slug:
            raise ValueError("Slug cannot be empty")
        return slug

    @field_validator("primary_color", "secondary_color", mode="before")
    @classmethod
    def validate_color(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v.startswith("#") or len(v) != 7:
            raise ValueError("Color must be a valid hex string, e.g. '#1e3a5f'")
        return v


class PageReorderItem(BaseModel):
    """Single item in a reorder request."""
    page_id: UUID
    sort_order: int


class PageReorderRequest(BaseModel):
    """Schema for reordering multiple pages."""
    pages: list[PageReorderItem]


# ─── Response schemas ─────────────────────────────────────────────────

class PublicPageResponse(BaseModel):
    """Full page response for admin endpoints."""
    id: UUID
    tenant_id: UUID
    title: str
    slug: str
    page_type: str
    content: dict[str, Any] | None = {}
    template: str | None = "default"
    primary_color: str | None = None
    secondary_color: str | None = None
    is_published: bool = False
    sort_order: int = 0
    meta_title: str | None = None
    meta_description: str | None = None
    show_in_nav: bool = True
    nav_label: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PublicPageListItem(BaseModel):
    """Lightweight page response for list endpoints."""
    id: UUID
    title: str
    slug: str
    page_type: str
    template: str | None = "default"
    is_published: bool = False
    sort_order: int = 0
    show_in_nav: bool = True
    nav_label: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PublicPagePublicResponse(BaseModel):
    """Public-facing page response (no tenant_id, only published content)."""
    id: UUID
    title: str
    slug: str
    page_type: str
    content: dict[str, Any] | None = {}
    template: str | None = "default"
    primary_color: str | None = None
    secondary_color: str | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    show_in_nav: bool = True
    nav_label: str | None = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PublicPageNavResponse(BaseModel):
    """Navigation item for public nav menus."""
    id: UUID
    title: str
    slug: str
    nav_label: str | None = None
    page_type: str
    sort_order: int = 0

    model_config = ConfigDict(from_attributes=True)
