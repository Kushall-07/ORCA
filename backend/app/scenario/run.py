"""Scenario runner CLI.

    python -m app.scenario.run --list
    python -m app.scenario.run --scenario 01_fisherman_safe
    python -m app.scenario.run --scenario fisherman_safe
    python -m app.scenario.run --all
    python -m app.scenario.run --all --json
    python -m app.scenario.run --perf 04_maritime_route --repeat 25

No Docker, no network: every scenario runs through the real LangGraph pipeline
with deterministic offline fixtures.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from app.scenario.library import SCENARIOS, by_id
from app.scenario.models import ScenarioReport
from app.scenario.runner import perf_probe, run_all, run_scenario

_GREEN = "\033[32m"
_RED = "\033[31m"
_DIM = "\033[2m"
_RESET = "\033[0m"


def _c(text: str, colour: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"{colour}{text}{_RESET}"


def _print_report(report: ScenarioReport) -> None:
    for r in report.results:
        tag = _c("PASS", _GREEN) if r.passed else _c("FAIL", _RED)
        print(f"{tag} {r.scenario_id:<32} {r.title}")
        if not r.passed:
            for line in r.failure_lines:
                print(f"     {_c('- ' + line, _RED)}")
    print()
    total = len(report.results)
    print(f"{report.passed} passed, {report.failed} failed  (of {total})")


def _report_to_dict(report: ScenarioReport) -> dict:
    return {
        "passed": report.passed,
        "failed": report.failed,
        "ok": report.ok,
        "results": [
            {
                "scenario_id": r.scenario_id,
                "title": r.title,
                "passed": r.passed,
                "duration_ms": r.duration_ms,
                "failures": list(r.failure_lines),
                "turns": [
                    {
                        "turn": t.turn_index,
                        "message": t.message,
                        "passed": t.passed,
                        "decision": t.decision,
                        "risk_level": t.risk_level,
                        "intent": t.intent,
                        "request_id": t.request_id,
                        "duration_ms": t.duration_ms,
                        "failures": list(t.failures),
                    }
                    for t in r.turns
                ],
            }
            for r in report.results
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.scenario.run")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--list", action="store_true", help="list scenarios and exit")
    g.add_argument("--scenario", metavar="ID", help="run one scenario by id or suffix")
    g.add_argument("--all", action="store_true", help="run every scenario")
    g.add_argument("--perf", metavar="ID", help="performance probe for one scenario")
    parser.add_argument("--repeat", type=int, default=20, help="iterations for --perf")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    if args.list:
        if args.json:
            print(json.dumps([
                {"scenario_id": s.scenario_id, "title": s.title,
                 "stakeholder": s.stakeholder, "fixture": s.fixture,
                 "tags": list(s.tags), "turns": len(s.turns)}
                for s in SCENARIOS
            ], indent=2))
        else:
            for s in SCENARIOS:
                who = s.stakeholder or "-"
                print(f"  {s.scenario_id:<32} [{who:<19}] {s.title}")
            print(f"\n{len(SCENARIOS)} scenarios")
        return 0

    if args.perf:
        scenario = by_id(args.perf)
        if scenario is None:
            print(f"unknown scenario: {args.perf}", file=sys.stderr)
            return 2
        result = asyncio.run(perf_probe(scenario, repeat=args.repeat))
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            tm = result["total_ms"]
            print(f"perf: {scenario.scenario_id}  n={result['repeat']}")
            print(f"  total   min={tm['min']:.1f}  median={tm['median']:.1f}  "
                  f"p95={tm['p95']:.1f}  max={tm['max']:.1f}  ms")
            for node, s in result["nodes"].items():
                print(f"  {node:<16} median={s['median']:.2f}  p95={s['p95']:.2f}  ms")
        return 0

    if args.scenario:
        scenario = by_id(args.scenario)
        if scenario is None:
            print(f"unknown scenario: {args.scenario}", file=sys.stderr)
            return 2
        report = ScenarioReport(results=(asyncio.run(run_scenario(scenario)),))
    else:
        report = asyncio.run(run_all(list(SCENARIOS)))

    if args.json:
        print(json.dumps(_report_to_dict(report), indent=2))
    else:
        _print_report(report)
    return 0 if report.ok else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
