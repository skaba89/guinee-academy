"""
Database Base metadata re-export.

Alembic's `env.py` imports `Base` from this module to access the
SQLAlchemy `MetaData` aggregating all registered models. The canonical
definition lives in `app.core.database` (where the SQLAlchemy engine
and SessionLocal are also created). We re-export it here so migration
scripts can keep using the conventional `from app.db.base import Base`
import path while the actual Base class stays co-located with the
engine/session setup.
"""

from app.core.database import Base

__all__ = ["Base"]
