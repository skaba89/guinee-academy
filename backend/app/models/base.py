"""Base model with common fields.

Provides mixins for UUID primary keys, timestamps, and tenant isolation.
Works with both PostgreSQL and SQLite backends.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, String, ForeignKey, TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid

from app.core.database import Base


class GUID(TypeDecorator):
    """Platform-independent GUID type.

    Uses PostgreSQL's native UUID type when available.
    Falls back to CHAR(36) for SQLite and other databases.

    Stores UUIDs in standard hyphenated string form (e.g. '67ed70da-6b17-477e-88c7-a0eb2d0f72e1')
    so that data inserted via raw SQL (Alembic migrations, init_db.py seed scripts)
    joins correctly with data inserted via the ORM.
    """
    impl = CHAR(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == "postgresql":
            # PostgreSQL native UUID accepts both str and uuid.UUID
            if isinstance(value, uuid.UUID):
                return str(value)
            return str(uuid.UUID(value))
        else:
            # SQLite / others: store as hyphenated string (CHAR(36))
            if isinstance(value, uuid.UUID):
                return str(value)
            # value is a string — normalize to hyphenated form
            # (handles both 32-char hex without hyphens and 36-char with hyphens)
            try:
                return str(uuid.UUID(value))
            except (ValueError, AttributeError):
                return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if isinstance(value, uuid.UUID):
                return value
            try:
                return uuid.UUID(str(value))
            except (ValueError, AttributeError):
                return value


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=datetime.now, nullable=False)


class UUIDMixin:
    """Mixin for UUID primary key (works with PostgreSQL and SQLite)"""
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)


class TenantMixin:
    """Mixin for tenant_id foreign key (works with PostgreSQL and SQLite)"""
    tenant_id = Column(GUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
