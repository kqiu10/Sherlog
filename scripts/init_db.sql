-- Runs automatically on first container start (docker-entrypoint-initdb.d).
-- Enables pgvector so we can store and similarity-search incident embeddings.
CREATE EXTENSION IF NOT EXISTS vector;
