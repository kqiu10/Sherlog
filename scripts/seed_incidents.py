"""Seed the incidents table from data/incidents/seed.json.

Run once (or after editing the seed file) to populate the RAG knowledge base:

    uv run python scripts/seed_incidents.py

Idempotent-ish: it truncates and reloads so re-running gives a clean, known set
rather than duplicates. Each incident's log is embedded and stored alongside it.
"""

import json
from pathlib import Path

from sherlog.db import connect, init_schema
from sherlog.embeddings import embed

SEED_FILE = Path(__file__).parent.parent / "data" / "incidents" / "seed.json"


def main() -> None:
    init_schema()
    incidents = json.loads(SEED_FILE.read_text())

    with connect() as conn, conn.cursor() as cur:
        # Reset so re-seeding is deterministic, not additive.
        cur.execute("TRUNCATE incidents RESTART IDENTITY")
        for inc in incidents:
            # We embed the log text, since that's what we match incoming failures against.
            vector = embed(inc["log"])
            cur.execute(
                "INSERT INTO incidents (title, log, root_cause, fix, embedding) "
                "VALUES (%s, %s, %s, %s, %s)",
                (inc["title"], inc["log"], inc["root_cause"], inc.get("fix"), vector),
            )
        conn.commit()

    print(f"Seeded {len(incidents)} incidents into the knowledge base.")


if __name__ == "__main__":
    main()
