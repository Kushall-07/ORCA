"""Phase 7 observability: structured node trace, timing, correlation id.

These assert the *enrichment* is real and that the Phase 5/6 ``agent_trace`` the
frontend depends on is untouched.
"""

from __future__ import annotations

from app.observability.trace import NodeStatus, summarise_durations
from tests.orchestration_fakes import NOW, make_pipeline


async def test_node_trace_is_populated_and_timed() -> None:
    r = await make_pipeline().run(
        message="Is it safe to go fishing from Mangalore now?",
        session_id="obs-1", request_id="req-obs-1", now=NOW,
    )
    assert r.request_id == "req-obs-1"
    assert r.node_trace, "node_trace should not be empty"

    names = [n.node for n in r.node_trace]
    assert names[0] == "understand"
    assert "risk" in names and "decision" in names and "assemble" in names

    for n in r.node_trace:
        assert n.status in {s.value for s in NodeStatus}
        assert n.duration_ms is not None and n.duration_ms >= 0.0
        assert n.started_at and n.ended_at
    # timestamps are monotonic in projection order
    starts = [n.started_at for n in r.node_trace]
    assert starts == sorted(starts)


async def test_agent_trace_is_unchanged_by_observability() -> None:
    r = await make_pipeline().run(
        message="Is it safe to go fishing from Mangalore now?",
        session_id="obs-2", now=NOW,
    )
    # still a flat list[str] of the frozen tokens, one per executed node
    assert isinstance(r.agent_trace, list)
    assert all(isinstance(t, str) for t in r.agent_trace)
    assert r.agent_trace[0] == "understand"
    assert r.agent_trace[-1] == "assemble"
    # every executed node contributed exactly one agent_trace token and one
    # node_trace record
    assert len(r.agent_trace) == len(r.node_trace)


async def test_skipped_nodes_are_marked_skipped() -> None:
    # a weather-only query never routes or scores suitability
    r = await make_pipeline().run(
        message="What is the wind at Chennai now?", session_id="obs-3", now=NOW,
    )
    by_name = {n.node: n for n in r.node_trace}
    assert by_name["suitability"].status == NodeStatus.SKIPPED.value
    assert by_name["suitability"].skipped is True


async def test_failed_node_is_recorded_as_failed() -> None:
    from tests.orchestration_fakes import FakeGisAgent

    r = await make_pipeline(gis=FakeGisAgent(fail=True)).run(
        message="Is it safe to go fishing from Mangalore now?",
        session_id="obs-4", now=NOW,
    )
    gis = next(n for n in r.node_trace if n.node == "collect_gis")
    assert gis.status == NodeStatus.FAILED.value
    assert gis.error_type


async def test_request_id_is_generated_when_absent() -> None:
    r = await make_pipeline().run(message="weather at Mangalore now", session_id="obs-5", now=NOW)
    assert r.request_id and r.request_id.startswith("req-")


def test_summarise_durations_percentiles() -> None:
    s = summarise_durations([10.0, 20.0, 30.0, 40.0, 1000.0])
    assert s["min"] == 10.0
    assert s["max"] == 1000.0
    assert s["median"] == 30.0
    assert s["p95"] >= s["median"]
    assert s["n"] == 5
    assert summarise_durations([])["n"] == 0


async def test_node_trace_and_request_id_survive_a_node_level_failure() -> None:
    # The understand node is internally defensive: an agent exception becomes a
    # graceful QUERY_UNDERSTANDING_FAILED, and observability still records it.
    class Boom:
        async def understand(self, *a, **k):  # noqa: ANN001, ANN002, ANN003
            raise RuntimeError("kaboom")

    pipe = make_pipeline()
    pipe.deps.qu_agent = Boom()
    pipe.graph = __import__(
        "app.orchestration.graph", fromlist=["build_orca_graph"]
    ).build_orca_graph(pipe.deps)
    r = await pipe.run(message="hello", session_id="obs-6", request_id="req-boom", now=NOW)
    assert r.status == "QUERY_UNDERSTANDING_FAILED"
    assert r.request_id == "req-boom"
    assert r.node_trace and r.node_trace[0].node == "understand"
    assert "traceback" not in r.answer.lower()
