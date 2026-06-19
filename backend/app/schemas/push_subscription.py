from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PushSubscriptionBase(BaseModel):
    endpoint: str
    p256dh: str
    auth: str
    platform: str | None = "web"
    is_active: bool | None = True

class PushSubscriptionCreate(PushSubscriptionBase):
    pass

class PushSubscriptionUpdate(BaseModel):
    is_active: bool | None = None

class PushSubscriptionInDB(PushSubscriptionBase):
    id: UUID
    user_id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
