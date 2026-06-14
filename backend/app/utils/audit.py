"""Utilities for audit logging"""
import logging
import uuid
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from typing import Optional, Any

logger = logging.getLogger(__name__)

def log_audit(
    db: Session,
    user_id: str,
    tenant_id: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[Any] = None,
    ip_address: Optional[str] = None,
    severity: Optional[str] = "INFO",
    user_agent: Optional[str] = None
):
    """
    Helper function to record an audit log entry.
    
    All ID parameters are coerced to strings to ensure compatibility with
    both PostgreSQL (native UUID) and SQLite (CHAR/String) backends.
    """
    try:
        # Coerce UUID objects to strings — SQLAlchemy's String column
        # cannot bind native uuid.UUID objects on SQLite.
        if isinstance(user_id, uuid.UUID):
            user_id = str(user_id)
        if isinstance(tenant_id, uuid.UUID):
            tenant_id = str(tenant_id)
        if isinstance(resource_id, uuid.UUID):
            resource_id = str(resource_id)
            
        audit_entry = AuditLog(
            user_id=str(user_id) if user_id else None,
            tenant_id=str(tenant_id) if tenant_id else None,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            details=details,
            ip_address=ip_address,
            severity=severity,
            user_agent=user_agent
        )
        db.add(audit_entry)
        db.flush() # Ensure it's prepared within the transaction
    except Exception as e:
        # We don't want audit logging to crash the main operation
        logger.error("Error recording audit log: %s", e)
