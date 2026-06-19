from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotificationBase(BaseModel):
    title: str
    message: str | None = None
    type: str | None = "info"
    link: str | None = None

class NotificationCreate(NotificationBase):
    user_id: UUID

class NotificationBulkCreate(BaseModel):
    notifications: list[NotificationCreate]

class NotificationUpdate(BaseModel):
    is_read: bool | None = None

class NotificationResponse(NotificationBase):
    id: UUID
    user_id: UUID
    tenant_id: UUID
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
