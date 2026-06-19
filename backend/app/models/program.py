from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class Program(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "programs"

    name = Column(String(255), nullable=False)
    code = Column(String(50))
    description = Column(String(500))

    # Relationships
    classes = relationship("Classroom", back_populates="program")
