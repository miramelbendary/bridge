"""Portable column types."""

from __future__ import annotations

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

# JSONB on PostgreSQL, plain JSON elsewhere (SQLite in local runs and tests).
JSONType = JSON().with_variant(JSONB(), "postgresql")
