from pathlib import Path

import sqlglot
from sqlglot import expressions as exp

MIGRATION = Path(__file__).parent.parent / "supabase" / "migrations" / "0001_init.sql"


def parsed_statements():
    return sqlglot.parse(MIGRATION.read_text(), read="postgres")


def created_tables() -> set[str]:
    return {
        stmt.find(exp.Table).name
        for stmt in parsed_statements()
        if isinstance(stmt, exp.Create) and stmt.kind == "TABLE"
    }


def test_migration_parses_as_postgres():
    assert len(parsed_statements()) > 0


def test_all_spec_tables_created():
    assert created_tables() == {"videos", "analytics", "taste_library", "templates"}


def test_videos_status_constraint_lists_all_pipeline_states():
    sql = MIGRATION.read_text()
    for status in (
        "ideation", "scripted", "assets_ready", "rendered",
        "qa_pending", "approved", "rejected", "published",
    ):
        assert f"'{status}'" in sql, f"missing status {status} in CHECK constraint"


def test_templates_seeded():
    sql = MIGRATION.read_text().lower()
    assert "insert into templates" in sql
    for name in ("explainer", "tutorial", "listicle", "comparison"):
        assert name in sql
