"""Central configuration, loaded from environment variables (and a local .env file).

Using pydantic-settings means every setting is typed, validated once at startup,
and documented in a single place instead of scattered os.getenv() calls.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Reads from a .env file if present; ignores unknown env vars instead of erroring.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    sherlog_model: str = "claude-sonnet-4-6"
    database_url: str = "postgresql://sherlog:sherlog@localhost:5432/sherlog"
    sherlog_max_iterations: int = 3


# Import this singleton anywhere config is needed: `from sherlog.config import settings`.
settings = Settings()
