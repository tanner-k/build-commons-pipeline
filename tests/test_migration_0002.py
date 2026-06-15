from pathlib import Path

import sqlglot

MIGRATION = Path(__file__).parent.parent / "supabase" / "migrations" / "0002_enhancement.sql"


def sql() -> str:
    return MIGRATION.read_text()


def test_parses_as_postgres():
    assert len(sqlglot.parse(sql(), read="postgres")) > 0


def test_adds_enhance_columns():
    text = sql().lower()
    for col in ("kind", "source_video_url", "transcript", "enhancement_json"):
        assert col in text, f"missing column {col}"


def test_kind_constraint_values():
    text = sql()
    assert "'generated'" in text and "'enhanced'" in text


def test_adds_new_statuses():
    text = sql()
    for status in ("uploaded", "plan_ready", "plan_approved"):
        assert f"'{status}'" in text, f"missing status {status}"
    # existing statuses must remain
    for status in ("assets_ready", "qa_pending", "approved", "published"):
        assert f"'{status}'" in text
