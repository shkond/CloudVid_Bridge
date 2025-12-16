"""Custom SQLAlchemy types for cross-database compatibility."""

import uuid
from typing import Any

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import CHAR, TypeDecorator


class GUID(TypeDecorator):
    """Platform-independent GUID type.

    Uses PostgreSQL's native UUID type when available,
    otherwise uses String(36) for SQLite compatibility.

    This solves the type mismatch error:
    "operator does not exist: uuid = character varying"

    Usage in models:
        id: Mapped[str] = mapped_column(GUID(), primary_key=True)
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        """Load the appropriate implementation based on dialect."""
        if dialect.name == "postgresql":
            # Use native UUID type for PostgreSQL
            return dialect.type_descriptor(PG_UUID(as_uuid=False))
        else:
            # Use String(36) for SQLite and others
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:
        """Convert UUID to string for storage."""
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return str(value)
        return value

    def process_result_value(self, value: Any, dialect: Any) -> str | None:
        """Convert stored value to string.

        Always return as string for consistency across databases.
        PostgreSQL may return UUID objects, SQLite returns strings.
        """
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(value)
