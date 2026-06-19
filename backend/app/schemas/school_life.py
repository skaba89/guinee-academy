from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


# --- Assessment Schemas ---

class AssessmentBase(BaseModel):
    name: str
    max_score: float = 20.0
    date: datetime
    assessment_type: str | None = None
    subject_id: UUID
    academic_year_id: UUID | None = None
    term_id: UUID | None = None

class AssessmentCreate(AssessmentBase):
    pass

class AssessmentUpdate(BaseModel):
    name: str | None = None
    max_score: float | None = None
    date: datetime | None = None
    assessment_type: str | None = None

class Assessment(AssessmentBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Grade Schemas ---

class GradeBase(BaseModel):
    student_id: UUID
    assessment_id: UUID | None = None
    subject_id: UUID | None = None
    score: float
    max_score: float = 20.0
    coefficient: float = 1.0
    comments: str | None = None

class GradeCreate(GradeBase):
    pass

class GradeUpdate(BaseModel):
    score: float | None = None
    max_score: float | None = None
    coefficient: float | None = None
    comments: str | None = None

class Grade(GradeBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    # Inclusion of Assessment and Student details for frontend
    assessment: Assessment | None = None

    class Config:
        from_attributes = True

# --- Attendance Schemas ---

class AttendanceBase(BaseModel):
    date: date
    status: str
    reason: str | None = None
    student_id: UUID
    subject_id: UUID | None = None
    classroom_id: UUID | None = None

class AttendanceCreate(AttendanceBase):
    pass

class AttendanceUpdate(BaseModel):
    status: str | None = None
    reason: str | None = None

class Attendance(AttendanceBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- School Event Schemas ---

class SchoolEventBase(BaseModel):
    title: str
    description: str | None = None
    start_date: datetime
    end_date: datetime | None = None
    location: str | None = None
    is_all_day: bool = False
    event_type: str | None = None

class SchoolEventCreate(SchoolEventBase):
    pass

class SchoolEventUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    location: str | None = None
    is_all_day: bool | None = None
    event_type: str | None = None

class SchoolEvent(SchoolEventBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Student Check-In Schemas ---

class StudentCheckInBase(BaseModel):
    checked_at: datetime
    direction: str = "IN"
    source: str | None = None
    student_id: UUID

class StudentCheckInCreate(StudentCheckInBase):
    pass

class StudentCheckIn(StudentCheckInBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
