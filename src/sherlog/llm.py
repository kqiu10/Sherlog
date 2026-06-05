"""Single place that builds the Claude chat model used by every agent.

Centralizing this means we configure the model/key once and each agent just calls
`get_llm()`. Swapping models or adding params later touches only this file.
"""

from functools import lru_cache

from langchain_anthropic import ChatAnthropic

from sherlog.config import settings


@lru_cache(maxsize=4)
def get_llm(model: str | None = None) -> ChatAnthropic:
    # Cached per model name so we can mix models (e.g. a cheap Haiku diagnostician with
    # a stronger Critic) without rebuilding clients. Defaults to settings.sherlog_model.
    return ChatAnthropic(
        model=model or settings.sherlog_model,
        api_key=settings.anthropic_api_key,
        temperature=0,  # deterministic-ish: diagnosis should be stable, not creative
        max_tokens=1024,
    )
