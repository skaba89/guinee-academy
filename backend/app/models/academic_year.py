from sqlalchemy import Boolean, Column, Date, String

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class AcademicYear(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "academic_years"

    name = Column(String, nullable=False)
    code = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_current = Column(Boolean, default=False)
