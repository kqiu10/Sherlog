"""LLM-as-judge for root-cause correctness, built on DeepEval's GEval.

We can't string-match a free-text diagnosis against the labeled cause — "null
baseUrl" and "API_URL is undefined" are the same answer in different words. So we
use a second LLM, given a strict rubric, to score semantic agreement on the *true
root cause*. DeepEval's GEval is the standard tool for this; we point it at Claude
(via DeepEval's native AnthropicModel) so no second vendor key is needed.
"""

import os

# Opt out of DeepEval's telemetry/network chatter before importing it.
os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")
os.environ.setdefault("DEEPEVAL_DISABLE_PROGRESS_BAR", "YES")

from dataclasses import dataclass  # noqa: E402

from deepeval.metrics import GEval  # noqa: E402
from deepeval.models import AnthropicModel  # noqa: E402
from deepeval.test_case import LLMTestCase, SingleTurnParams  # noqa: E402

from sherlog.config import settings  # noqa: E402


@dataclass
class Judgement:
    passed: bool      # did the diagnosis match the true root cause (score >= threshold)?
    score: float      # GEval's 0-1 correctness score
    reason: str       # the judge's justification


def _build_metric() -> GEval:
    judge_model = AnthropicModel(
        model=settings.sherlog_model,
        api_key=settings.anthropic_api_key,
        temperature=0,  # judging should be stable across runs
    )
    return GEval(
        name="Root Cause Correctness",
        model=judge_model,
        evaluation_params=[
            SingleTurnParams.INPUT,            # the failure log
            SingleTurnParams.ACTUAL_OUTPUT,    # Sherlog's diagnosed root cause
            SingleTurnParams.EXPECTED_OUTPUT,  # the human-labeled true root cause
        ],
        evaluation_steps=[
            "Identify the true root cause described in the EXPECTED OUTPUT.",
            "Determine whether the ACTUAL OUTPUT identifies that same underlying root "
            "cause for the failure shown in the INPUT.",
            "Reward semantic agreement on the true cause. Do NOT penalize differences in "
            "wording, extra detail, or any fix suggestions included in the ACTUAL OUTPUT.",
            "Fail the case if the ACTUAL OUTPUT names a different or incorrect root cause, "
            "or only restates the symptom without identifying the cause.",
        ],
        threshold=0.5,
    )


# Build the metric once and reuse it across all cases.
_metric = None


def judge_root_cause(log: str, expected: str, actual: str) -> Judgement:
    """Score whether `actual` diagnosis captures the same root cause as `expected`."""
    global _metric
    if _metric is None:
        _metric = _build_metric()

    test_case = LLMTestCase(input=log, actual_output=actual, expected_output=expected)
    _metric.measure(test_case)
    return Judgement(
        passed=bool(_metric.success),
        score=float(_metric.score or 0.0),
        reason=_metric.reason or "",
    )
