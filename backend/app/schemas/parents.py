from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


# --- ParentStudent Schemas ---

class ParentStudentBase(BaseModel):
    parent_id: UUID
    student_id: UUID
    is_primary: bool = False
    relation_type: str | None = None

class ParentStudentCreate(ParentStudentBase):
    pass

class ParentStudent(ParentStudentBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- API Endpoints and CRUD logic (Simplified internal) ---
# This will be used in the router
