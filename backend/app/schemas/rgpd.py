from datetime import datetime

from pydantic import UUID4, BaseModel


class DeletionRequestBase(BaseModel):
    reason: str | None = None

class DeletionRequestCreate(DeletionRequestBase):
    pass

class DeletionRequestUpdate(BaseModel):
    status: str
    rejection_reason: str | None = None

class UserMin(BaseModel):
    id: UUID4
    email: str
    first_name: str | None = None
    last_name: str | None = None

    class Config:
        from_attributes = True

class DeletionRequestInDB(DeletionRequestBase):
    id: UUID4
    tenant_id: UUID4
    user_id: UUID4
    status: str
    requested_at: datetime
    processed_at: datetime | None = None
    processed_by: UUID4 | None = None
    rejection_reason: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DeletionRequest(DeletionRequestInDB):
    user: UserMin | None = None
    processor: UserMin | None = None
