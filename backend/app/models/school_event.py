from sqlalchemy import Boolean, Column, DateTime, String, Text

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class SchoolEvent(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "school_events"

    title = Column(String(255), nullable=False)
    description = Column(Text)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)
    location = Column(String(255))
    is_all_day = Column(Boolean, default=False)
    event_type = Column(String(50)) # HOLIDAY, EXAM, MEETING, etc.
