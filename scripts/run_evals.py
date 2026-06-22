#!/usr/bin/env python3
"""
scripts/run_evals.py
─────────────────────
LLM evaluation harness.
Defines eval suites, runs them against the live agent, scores results,
and exits non-zero if the pass rate falls below the threshold.

Usage:
    python scripts/run_evals.py --suite all --output eval_results.json --fail-threshold 0.80
"""

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, field
from typing import Any, Callable

from src.agents.orchestrator import OrchestratorAgent
from src.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


@dataclass
class EvalCase:
    name: str
    prompt: str
    suite: str
    check: Callable[[str], bool]
    weight: float = 1.0


@dataclass
class EvalResult:
    name: str
    suite: str
    passed: bool
    score: float
    answer: str = ""
    error: str = ""


# ── Eval suite definitions ────────────────────────────────────

EVAL_CASES: list[EvalCase] = [
    # Reasoning
    EvalCase(
        name="basic_math",
        suite="agents",
        prompt="What is 17 multiplied by 23?",
        check=lambda a: "391" in a,
    ),
    EvalCase(
        name="capital_city",
        suite="agents",
        prompt="What is the capital of France?",
        check=lambda a: "paris" in a.lower(),
    ),
    EvalCase(
        name="code_fibonacci",
        suite="agents",
        prompt="Write a Python function to compute the nth Fibonacci number recursively.",
        check=lambda a: "def" in a and "fibonacci" in a.lower(),
    ),
    # Tool use
    EvalCase(
        name="tool_code_exec",
        suite="tools",
        prompt="Use the code execution tool to compute the square root of 144.",
        check=lambda a: "12" in a,
        weight=1.5,
    ),
    EvalCase(
        name="tool_file_roundtrip",
        suite="tools",
        prompt="Write 'eval_test_content' to a file called eval_check.txt, then read it back.",
        check=lambda a: "eval_test_content" in a,
        weight=1.5,
    ),
    # RAG (will return empty context in eval env — just test it doesn't crash)
    EvalCase(
        name="rag_graceful_empty",
        suite="rag",
        prompt="What does the knowledge base say about quantum entanglement?",
        check=lambda a: len(a) > 20,  # Just verify a coherent response
    ),
]


# ── Runner ────────────────────────────────────────────────────

async def run_eval(agent: OrchestratorAgent, case: EvalCase) -> EvalResult:
    logger.info("eval_running", name=case.name, suite=case.suite)
    try:
        result = await agent.run_with_delegation(case.prompt)
        answer = result.get("answer", "")
        passed = case.check(answer)
        score = case.weight if passed else 0.0
        return EvalResult(name=case.name, suite=case.suite, passed=passed, score=score, answer=answer[:300])
    except Exception as exc:
        logger.error("eval_error", name=case.name, error=str(exc))
        return EvalResult(name=case.name, suite=case.suite, passed=False, score=0.0, error=str(exc))


async def main(suite: str, output: str, fail_threshold: float) -> None:
    configure_logging()
    agent = OrchestratorAgent()

    cases = EVAL_CASES if suite == "all" else [c for c in EVAL_CASES if c.suite == suite]
    if not cases:
        logger.error("no_eval_cases_found", suite=suite)
        sys.exit(1)

    logger.info("evals_starting", total=len(cases), suite=suite)
    results = await asyncio.gather(*[run_eval(agent, c) for c in cases])

    total_weight = sum(c.weight for c in cases)
    earned_weight = sum(r.score for r in results)
    pass_rate = earned_weight / total_weight if total_weight > 0 else 0.0

    # Write results
    serialised = [
        {"name": r.name, "suite": r.suite, "passed": r.passed, "score": r.score,
         "answer": r.answer, "error": r.error}
        for r in results
    ]
    with open(output, "w") as f:
        json.dump(serialised, f, indent=2)

    passed = sum(1 for r in results if r.passed)
    logger.info(
        "evals_complete",
        passed=passed,
        total=len(results),
        pass_rate=f"{pass_rate:.1%}",
        threshold=f"{fail_threshold:.1%}",
    )

    print(f"\n{'='*50}")
    print(f"  Eval Results: {passed}/{len(results)} passed ({pass_rate:.1%})")
    print(f"  Threshold:    {fail_threshold:.1%}")
    print(f"{'='*50}")
    for r in results:
        icon = "✅" if r.passed else "❌"
        print(f"  {icon}  {r.name:<30} score={r.score}")
    print()

    if pass_rate < fail_threshold:
        print(f"❌ Pass rate {pass_rate:.1%} is below threshold {fail_threshold:.1%}. Failing.")
        sys.exit(1)

    print("✅ All evals passed threshold.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", default="all")
    parser.add_argument("--output", default="eval_results.json")
    parser.add_argument("--fail-threshold", type=float, default=0.80)
    args = parser.parse_args()
    asyncio.run(main(args.suite, args.output, args.fail_threshold))
