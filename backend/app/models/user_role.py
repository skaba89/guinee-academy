from sqlalchemy import Column, String, ForeignKey, UniqueConstraint
from app.models.base import Base, UUIDMixin, TimestampMixin, GUID


class UserRole(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "user_roles"
    __table_args__ = (
        # Prevent duplicate role assignments: a user can only have a given role
        # once per tenant. Without this, concurrent requests or UI bugs could
        # create duplicate rows causing confusing results.
        UniqueConstraint("user_id", "tenant_id", "role", name="uq_user_roles_user_tenant_role"),
    )

    # tenant_id nullable — SUPER_ADMIN role is not tenant-scoped
    tenant_id = Column(GUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)

    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(50), nullable=False)
