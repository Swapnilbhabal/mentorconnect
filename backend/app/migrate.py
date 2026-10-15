"""Additive auto-migration, run once on every backend startup.

The project's schema has only ever grown (new columns, new tables) and never renamed or
dropped anything. `Base.metadata.create_all()` already creates any table that doesn't exist
yet, but it silently does NOT add new columns to a table that already exists -- which used to
mean deleting the whole database file every time a column was added, losing every registered
account and booking just to pick up one new field.

This closes that gap: on startup, for every table SQLAlchemy knows about, compare its actual
columns (via SQLite's own introspection) against the columns the current models declare, and
`ALTER TABLE ... ADD COLUMN ...` for anything missing. Existing rows simply get NULL in the new
column, exactly as if the row had been created before that field existed -- which is true.

This is intentionally simple, not a full migration framework: it only ever ADDS columns, never
renames, drops, or changes a column's type. That has been sufficient for every schema change
this project has made so far. If a future change genuinely needs a rename/drop, that one still
needs a manual one-time fix (or, at that point, adopting a real migration tool like Alembic).
"""
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from .database import Base


def auto_migrate(engine: Engine) -> list[str]:
    """Returns a list of human-readable descriptions of what it changed, for startup logging."""
    changes = []
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue  # brand-new table: create_all() already handled it before this runs
            existing_columns = {col["name"] for col in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing_columns:
                    continue
                col_type = column.type.compile(dialect=engine.dialect)
                conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {col_type}'))
                changes.append(f"{table.name}.{column.name} ({col_type})")

    return changes