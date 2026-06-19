"""
Serialization helpers that work uniformly across SQLite and PostgreSQL.

SQLite returns datetimes/dates as strings; PostgreSQL returns datetime/date objects.
Use these helpers instead of `value.isoformat()` to support both backends.
"""
from datetime import datetime, date
from typing import Optional, Any


def to_iso(val: Any) -> Optional[str]:
    """Convert a datetime, date, or string to an ISO-format string.

    - datetime → val.isoformat()
    - date → val.isoformat()
    - str → returned as-is (SQLite already returns ISO strings)
    - None → None
    - anything else → str(val)
    """
    if val is None:
        return None
    if isinstance(val, str):
        return val
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    return str(val)


def to_iso_list(items: list, field: str) -> list:
    """Apply to_iso to a specific field across a list of dicts."""
    for item in items:
        if field in item:
            item[field] = to_iso(item[field])
    return items
