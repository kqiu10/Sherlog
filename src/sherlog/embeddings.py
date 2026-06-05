"""Local text embeddings via fastembed.

We embed locally (no external embeddings API) so the only credential Sherlog needs
is the Claude key. The model `BAAI/bge-small-en-v1.5` is small, fast (ONNX, no
torch), and produces 384-dimensional vectors — the dimension the DB schema expects.

The model is downloaded once on first use and cached under ~/.cache/fastembed.
"""

from functools import lru_cache

from fastembed import TextEmbedding

EMBED_MODEL = "BAAI/bge-small-en-v1.5"
EMBED_DIM = 384  # must match the vector(N) column in scripts/init_db schema


@lru_cache(maxsize=1)
def _model() -> TextEmbedding:
    # Lazy singleton: loading the model is expensive, so do it once and reuse.
    return TextEmbedding(model_name=EMBED_MODEL)


def embed(text: str) -> list[float]:
    """Embed a single string into a 384-dim vector."""
    # fastembed yields numpy arrays; take the first (and only) one and listify.
    vector = next(iter(_model().embed([text])))
    return vector.tolist()
