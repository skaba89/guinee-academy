from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


# --- Academic Year ---
class AcademicYearBase(BaseModel):
    name: str
    code: str
    start_date: date
    end_date: date
    is_current: bool = False

class AcademicYearCreate(AcademicYearBase):
    pass

class AcademicYearUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool | None = None

class AcademicYear(AcademicYearBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Term ---
class AcademicYearRef(BaseModel):
    name: str

class TermBase(BaseModel):
    academic_year_id: UUID
    name: str
    start_date: date
    end_date: date
    sequence_number: int = 1
    is_active: bool = False

class TermCreate(TermBase):
    pass

class TermUpdate(BaseModel):
    name: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    sequence_number: int | None = None
    is_active: bool | None = None

class Term(TermBase):
    id: UUID
    tenant_id: UUID
    academic_year: AcademicYearRef | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Campus ---
class CampusBase(BaseModel):
    name: str
    address: str | None = None
    phone: str | None = None
    is_main: bool = False

class CampusCreate(CampusBase):
    pass

class CampusUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    phone: str | None = None
    is_main: bool | None = None

class Campus(CampusBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Level ---
class LevelBase(BaseModel):
    name: str
    code: str | None = None
    label: str | None = None
    order_index: int = 0

class LevelCreate(LevelBase):
    pass

class LevelUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    label: str | None = None
    order_index: int | None = None

class Level(LevelBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Subject ---
class SubjectBase(BaseModel):
    name: str
    code: str | None = None
    coefficient: float | None = 1.0
    ects: float | None = 0
    cm_hours: int | None = 0
    td_hours: int | None = 0
    tp_hours: int | None = 0
    description: str | None = None

    @field_validator('coefficient', 'ects', 'cm_hours', 'td_hours', 'tp_hours', mode='before')
    @classmethod
    def _none_to_default(cls, v):
        """Treat NULL DB values as the schema default (0 / 1.0)."""
        return 0 if v is None else v

    @field_validator('coefficient', mode='after')
    @classmethod
    def _coerce_coefficient(cls, v):
        return 1.0 if (v is None or v == 0) else v

class SubjectCreate(SubjectBase):
    department_ids: list[UUID] | None = None
    level_ids: list[UUID] | None = None

class SubjectUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    coefficient: float | None = None
    ects: float | None = None
    cm_hours: int | None = None
    td_hours: int | None = None
    tp_hours: int | None = None
    description: str | None = None
    department_ids: list[UUID] | None = None
    level_ids: list[UUID] | None = None

class Subject(SubjectBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Department ---
class DepartmentBase(BaseModel):
    name: str
    code: str | None = None
    description: str | None = None
    head_id: UUID | None = None

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    description: str | None = None
    head_id: UUID | None = None

class Department(DepartmentBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Program ---
class ProgramBase(BaseModel):
    name: str
    code: str | None = None
    description: str | None = None

class ProgramCreate(ProgramBase):
    pass

class ProgramUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    description: str | None = None

class Program(ProgramBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Room ---
class RoomBase(BaseModel):
    name: str
    capacity: int | None = None
    campus_id: UUID | None = None

class RoomCreate(RoomBase):
    pass

class RoomUpdate(BaseModel):
    name: str | None = None
    capacity: int | None = None
    campus_id: UUID | None = None

class Room(RoomBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Classroom (Classes) ---
class ClassroomBase(BaseModel):
    name: str
    capacity: int | None = None
    level_id: UUID | None = None
    campus_id: UUID | None = None
    program_id: UUID | None = None
    academic_year_id: UUID | None = None
    main_room_id: UUID | None = None

class ClassroomCreate(ClassroomBase):
    department_ids: list[UUID] | None = None

class ClassroomUpdate(BaseModel):
    name: str | None = None
    capacity: int | None = None
    level_id: UUID | None = None
    campus_id: UUID | None = None
    program_id: UUID | None = None
    academic_year_id: UUID | None = None
    main_room_id: UUID | None = None
    department_ids: list[UUID] | None = None

class Classroom(ClassroomBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Enrollment ---
class EnrollmentBase(BaseModel):
    student_id: UUID
    class_id: UUID
    academic_year_id: UUID
    enrollment_date: date | None = None
    status: str = "ACTIVE"

class EnrollmentCreate(EnrollmentBase):
    pass

class EnrollmentUpdate(BaseModel):
    class_id: UUID | None = None
    academic_year_id: UUID | None = None
    enrollment_date: date | None = None
    status: str | None = None

class Enrollment(EnrollmentBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
