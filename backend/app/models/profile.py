from sqlalchemy import Column, ForeignKey, String

from app.models.base import GUID, Base, TimestampMixin, UUIDMixin


class Profile(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "profiles"

    id = Column(GUID(), ForeignKey("users.id"), primary_key=True)
    tenant_id = Column(GUID(), ForeignKey("tenants.id"))
    phone = Column(String)
    avatar_url = Column(String)
