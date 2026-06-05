"""Single place that builds the Claude chat model used by every agent.

Centralizing this means we configure the model/key once and each agent just calls
`get_llm()`. Swapping models or adding params later touches only this file.
"""

from functools import lru_cache

from langchain_anthropic import ChatAnthropic

from sherlog.config import settings


@lru_cache(maxsize=1)
def get_llm() -> ChatAnthropic:
    # lru_cache makes this a lazy singleton: built on first use, reused after.
    return ChatAnthropic(
        model=settings.sherlog_model,
        api_key=settings.anthropic_api_key,
        temperature=0,  # deterministic-ish: diagnosis should be stable, not creative
        max_tokens=1024,
    )
