from sqlalchemy import Boolean, Column, ForeignKey, String
from sqlalchemy.orm import relationship

from app.models.base import GUID, Base, TenantMixin, TimestampMixin, UUIDMixin


class ParentStudent(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "parent_students"

    parent_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(GUID(), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    is_primary = Column(Boolean, default=False)
    relation_type = Column(String(50)) # FATHER, MOTHER, GUARDIAN, etc.

    # Relationships
    parent = relationship("User")
    student = relationship("Student")
