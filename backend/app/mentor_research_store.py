"""Notebook research memory stored separately from concurrently edited workspaces."""
import json
from contextlib import closing
from backend.app import database


def _prepare(connection):
    connection.execute("""CREATE TABLE IF NOT EXISTS mentor_research_memory (
        workspace_id TEXT NOT NULL, notebook_id TEXT NOT NULL,
        state_json TEXT NOT NULL, PRIMARY KEY (workspace_id, notebook_id)
    )""")


def load_research_state(workspace_id: str, notebook_id: str) -> dict:
    with closing(database.get_connection()) as connection, connection:
        _prepare(connection)
        row = connection.execute(
            "SELECT state_json FROM mentor_research_memory WHERE workspace_id=? AND notebook_id=?",
            (workspace_id, notebook_id),
        ).fetchone()
    return json.loads(row[0]) if row else {}


def save_research_state(workspace_id: str, notebook_id: str, state: dict):
    with closing(database.get_connection()) as connection, connection:
        _prepare(connection)
        connection.execute(
            "INSERT INTO mentor_research_memory VALUES (?, ?, ?) "
            "ON CONFLICT(workspace_id, notebook_id) DO UPDATE SET state_json=excluded.state_json",
            (workspace_id, notebook_id, json.dumps(state, ensure_ascii=False)),
        )
