from datetime import datetime
from typing import Any

from pydantic import UUID4, BaseModel


class AuditLogBase(BaseModel):
    action: str
    severity: str | None = "INFO"
    resource_type: str
    resource_id: str | None = None
    details: dict[str, Any] | None = None

class AuditLogCreate(AuditLogBase):
    pass

class AuditLog(AuditLogBase):
    id: UUID4
    tenant_id: UUID4
    user_id: UUID4 | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True
