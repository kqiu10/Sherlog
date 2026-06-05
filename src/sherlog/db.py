"""Postgres + pgvector access layer.

Thin helpers around psycopg3: open a connection, register the pgvector type
adapter (so Python lists map to/from the SQL `vector` type), and ensure the
schema exists. Keeping all SQL here means agents never write raw SQL inline.
"""

import psycopg
from pgvector.psycopg import register_vector

from sherlog.config import settings
from sherlog.embeddings import EMBED_DIM

# One table: each row is a past incident (its log) plus the resolved root cause,
# embedded so we can similarity-search for incidents like the current failure.
SCHEMA_SQL = f"""
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS incidents (
    id          SERIAL PRIMARY KEY,
    title       TEXT NOT NULL,
    log         TEXT NOT NULL,
    root_cause  TEXT NOT NULL,
    fix         TEXT,
    embedding   vector({EMBED_DIM}) NOT NULL
);
"""


def connect() -> psycopg.Connection:
    """Open a connection with the pgvector adapter registered."""
    conn = psycopg.connect(settings.database_url)
    register_vector(conn)
    return conn


def init_schema() -> None:
    """Create the incidents table (idempotent)."""
    with connect() as conn, conn.cursor() as cur:
        cur.execute(SCHEMA_SQL)
        conn.commit()


def search_similar(embedding: list[float], k: int = 3) -> list[dict]:
    """Return the k most similar past incidents to the given embedding.

    Uses pgvector's `<=>` cosine-distance operator (smaller = more similar).
    """
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            # Cast the parameter to `vector` explicitly: with no column-type context
            # here, psycopg would otherwise send the list as a SQL float array, which
            # the `<=>` operator doesn't accept.
            """
            SELECT title, log, root_cause, fix, embedding <=> %s::vector AS distance
            FROM incidents
            ORDER BY distance
            LIMIT %s
            """,
            (embedding, k),
        )
        rows = cur.fetchall()
        cols = [c.name for c in cur.description]
        return [dict(zip(cols, row, strict=True)) for row in rows]
