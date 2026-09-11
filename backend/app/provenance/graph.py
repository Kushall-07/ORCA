"""Build the Decision Provenance Graph from the pipeline's typed results.

Every important claim becomes an explicit node with an edge back towards the
user query. Numeric nodes are what the grounding check verifies against.
"""

from __future__ import annotations

from app.models.advisory import MarineAdvisory
from app.models.conflict import Conflict
from app.models.decision import DecisionResult
from app.models.environmental import (
    EnvironmentalComparisonResult,
    EnvironmentalEvidenceResult,
    EnvironmentalNeighbourhoodResult,
    EnvironmentalProductivityResult,
    EnvironmentalStabilityResult,
)
from app.models.fabric import MarineDataFabric
from app.models.gis_agent import GisQueryResult
from app.models.pfz import PfzReferenceResult
from app.models.provenance import (
    ProvEdge,
    ProvenanceGraph,
    ProvNode,
    ProvNodeKind,
)
from app.models.query import QueryUnderstanding
from app.models.risk import FactorStatus, RiskResult
from app.models.routing import RouteResult, RouteStatus
from app.models.safety import SafetyGuardResult
from app.models.suitability import SuitabilityResult
from app.reasoning.arbitration import ArbitrationOutput
from app.reasoning.fusion import FusionResult

_AGENT_RESULT = ProvNodeKind.AGENT_RESULT


def build_provenance(
    *,
    message: str,
    understanding: QueryUnderstanding | None,
    weather_tier: str | None = None,
    ocean_tier: str | None = None,
    environment_tier: str | None = None,
    advisory: MarineAdvisory | None = None,
    advisory_tier: str | None = None,
    pfz: PfzReferenceResult | None = None,
    gis: GisQueryResult | None = None,
    fabric: MarineDataFabric | None = None,
    fusion: FusionResult | None = None,
    arbitration: ArbitrationOutput | None = None,
    conflicts: tuple[Conflict, ...] = (),
    suitability: SuitabilityResult | None = None,
    risk: RiskResult | None = None,
    safety: SafetyGuardResult | None = None,
    decision: DecisionResult | None = None,
    route: RouteResult | None = None,
    productivity: EnvironmentalProductivityResult | None = None,
    comparison: EnvironmentalComparisonResult | None = None,
    evidence: EnvironmentalEvidenceResult | None = None,
    stability: EnvironmentalStabilityResult | None = None,
    neighbourhood: EnvironmentalNeighbourhoodResult | None = None,
) -> ProvenanceGraph:
    nodes: list[ProvNode] = []
    edges: list[ProvEdge] = []

    def add(node: ProvNode, *parents: str, relation: str = "derived_from") -> str:
        nodes.append(node)
        for p in parents:
            edges.append(ProvEdge(src=p, dst=node.id, relation=relation))
        return node.id

    root = add(ProvNode(id="query", kind=ProvNodeKind.QUERY, label="user query",
                        value=message[:180]))

    intent_id = None
    if understanding is not None:
        intent_id = add(
            ProvNode(
                id="intent", kind=ProvNodeKind.INTENT,
                label=f"intent={understanding.intent.value}",
                value=understanding.intent.value,
                detail={
                    "language": understanding.language.value,
                    "understood_via": understanding.understood_via,
                    "confidence": f"{understanding.confidence:.2f}",
                },
            ),
            root,
        )

    parent_for_data = intent_id or root

    # ---- agent result summaries ----
    if weather_tier:
        add(ProvNode(id="agent:weather", kind=_AGENT_RESULT, label="weather agent",
                     value=weather_tier, source="open-meteo-forecast"), parent_for_data)
    if ocean_tier:
        add(ProvNode(id="agent:ocean", kind=_AGENT_RESULT, label="oceanographic agent",
                     value=ocean_tier, source="open-meteo-marine"), parent_for_data)
    if gis is not None:
        add(ProvNode(id="agent:gis", kind=_AGENT_RESULT, label="GIS & geofencing agent",
                     value=gis.backend, source=gis.source_status.source), parent_for_data)
    if environment_tier:
        add(ProvNode(id="agent:environment", kind=_AGENT_RESULT,
                     label="environmental (ocean-colour) agent",
                     value=environment_tier, source="noaa-coastwatch-erddap"), parent_for_data)
    advisory_agent_id = None
    if advisory_tier:
        advisory_agent_id = add(
            ProvNode(id="agent:advisory", kind=_AGENT_RESULT,
                     label="official marine advisory agent (IMD)",
                     value=advisory_tier, source="imd-sea-area-bulletin"),
            parent_for_data,
        )

    # ---- observations + validity ----
    obs_ids: dict[str, list[str]] = {}
    if fabric is not None:
        for i, rec in enumerate(fabric.records):
            o = rec.observation
            oid = f"obs:{o.variable}:{i}"
            src_agent = (
                "agent:weather" if o.source == "open-meteo-forecast"
                else "agent:ocean" if o.source == "open-meteo-marine"
                else "agent:environment" if str(o.source).startswith(
                    ("noaa-coastwatch-erddap", "incois-erddap", "orca-demo-environmental")
                ) and any(n.id == "agent:environment" for n in nodes)
                else "agent:advisory" if str(o.source).startswith("imd-sea-area-bulletin")
                and any(n.id == "agent:advisory" for n in nodes)
                else "agent:gis" if any(n.id == "agent:gis" for n in nodes)
                else parent_for_data
            )
            add(
                ProvNode(
                    id=oid, kind=ProvNodeKind.OBSERVATION,
                    label=o.variable, value=o.value, unit=o.unit,
                    source=o.source, source_tier=int(o.source_tier),
                    validity=rec.validity.value,
                    signal_kind=o.signal_kind.value if hasattr(o.signal_kind, "value") else str(o.signal_kind),
                    timestamp=o.valid_from or o.observed_at,
                    detail={"data_tier": rec.source_status.tier.value},
                ),
                src_agent if any(n.id == src_agent for n in nodes) else parent_for_data,
            )
            add(
                ProvNode(id=f"validity:{o.variable}:{i}", kind=ProvNodeKind.VALIDITY,
                         label=f"{o.variable} -> {rec.validity.value}",
                         value=rec.validity.value, detail={"reason": rec.validity_reason or ""}),
                oid,
            )
            obs_ids.setdefault(o.variable, []).append(oid)

    # ---- fusion ----
    fusion_ids: dict[str, str] = {}
    if fusion is not None:
        for vf in fusion.variables:
            fid = f"fusion:{vf.variable}"
            add(
                ProvNode(
                    id=fid, kind=ProvNodeKind.FUSION,
                    label=f"fusion({vf.variable})",
                    value=vf.conflict_kind.value,
                    detail={
                        "sources": ",".join(vf.sources),
                        "aligned": str(len(vf.aligned)),
                        "conflict": str(vf.conflict),
                        "spread": "" if vf.value_spread is None else f"{vf.value_spread}",
                    },
                ),
                *obs_ids.get(vf.variable, [parent_for_data]),
            )
            fusion_ids[vf.variable] = fid

    # ---- arbitration ----
    arb_ids: dict[str, str] = {}
    if arbitration is not None:
        for va in arbitration.variables:
            aid = f"arb:{va.variable}"
            add(
                ProvNode(
                    id=aid, kind=ProvNodeKind.ARBITRATION,
                    label=f"arbitration({va.variable})",
                    value=va.chosen_value if va.resolved else va.reason,
                    unit=None,
                    source=va.chosen_source,
                    source_tier=va.chosen_tier,
                    signal_kind=va.chosen_signal_kind,
                    detail={"resolved": str(va.resolved), "reason": va.reason},
                ),
                fusion_ids.get(va.variable, parent_for_data),
            )
            arb_ids[va.variable] = aid

    # ---- conflicts ----
    for i, c in enumerate(conflicts):
        add(
            ProvNode(
                id=f"conflict:{i}", kind=ProvNodeKind.CONFLICT,
                label=c.conflict_type.value, value=c.detail[:160],
                detail={
                    "severity": c.severity.value,
                    "resolution": c.resolution_status.value,
                    "sources": ",".join(c.sources),
                },
            ),
            arb_ids.get(c.variable or "", parent_for_data),
        )

    # ---- suitability ----
    suit_id = None
    if suitability is not None:
        suit_id = add(
            ProvNode(
                id="suitability", kind=ProvNodeKind.SUITABILITY,
                label="fishing suitability (ORCA-derived)",
                value=suitability.score if suitability.score is not None else suitability.level.value,
                detail={
                    "level": suitability.level.value,
                    "pfz_reference_present": str(suitability.pfz_reference_present),
                    "disclaimer": suitability.disclaimer,
                },
            ),
            *[arb_ids.get(v, parent_for_data) for v in ("wave_height", "wind_speed")],
        )

    # ---- environmental productivity (Phase 9 Step 3; never feeds safety) ----
    if productivity is not None:
        def _env_parent(variable: str) -> str:
            if variable in arb_ids:
                return arb_ids[variable]
            ids = obs_ids.get(variable)
            return ids[-1] if ids else parent_for_data

        detail = {
            "productivity_potential": productivity.productivity_potential.value,
            "data_sufficiency": productivity.data_sufficiency.value,
            "confidence": productivity.confidence.value,
            "engine_version": productivity.engine_version,
            "disclaimer": productivity.disclaimer,
        }
        if productivity.chlorophyll_class is not None:
            detail["chlorophyll_class"] = productivity.chlorophyll_class.value
        if productivity.chlorophyll_a is not None and productivity.chlorophyll_a.value is not None:
            detail["chlorophyll_a"] = f"{productivity.chlorophyll_a.value}"
        if productivity.sst is not None and productivity.sst.value is not None:
            detail["sea_surface_temperature"] = f"{productivity.sst.value}"
        env_parents = list(dict.fromkeys(
            [_env_parent("chlorophyll_a"), _env_parent("sea_surface_temperature")]
        ))
        add(
            ProvNode(
                id="productivity", kind=ProvNodeKind.ENVIRONMENTAL,
                label="environmental productivity potential (ORCA-derived)",
                value=productivity.productivity_potential.value,
                detail=detail,
            ),
            *env_parents,
        )

    # ---- environmental temporal comparison (Phase 9 Step 4; never feeds safety) ----
    if comparison is not None and (
        comparison.sst is not None or comparison.chlorophyll_a is not None
    ):
        history_id = add(
            ProvNode(
                id="agent:environment_history", kind=_AGENT_RESULT,
                label="historical environmental agent (ORCA-computed reference)",
                value=comparison.reference_window or "reference window",
                source="open-meteo-marine + noaa-coastwatch-erddap (past window)",
            ),
            parent_for_data,
        )

        def _cmp_obs_node(var: str, o, role: str, parent: str) -> str:
            oid = f"cmp_obs:{var}:{role}"
            add(
                ProvNode(
                    id=oid, kind=ProvNodeKind.OBSERVATION,
                    label=f"{var} ({role})",
                    value=o.value, unit=o.unit,
                    source=o.source, source_tier=int(o.source_tier),
                    validity=o.validity,
                    detail={
                        "data_tier": o.data_tier, "role": role,
                        "conflicted": str(o.conflicted),
                        "observed_at": o.observed_at or "",
                    },
                ),
                parent,
            )
            add(
                ProvNode(
                    id=f"cmp_validity:{var}:{role}", kind=ProvNodeKind.VALIDITY,
                    label=f"{var} {role} -> {o.validity}",
                    value=o.validity,
                ),
                oid,
            )
            return oid

        for var, cmp in (
            ("sea_surface_temperature", comparison.sst),
            ("chlorophyll_a", comparison.chlorophyll_a),
        ):
            if cmp is None:
                continue
            cmp_parents: list[str] = []
            if cmp.current is not None and cmp.current.value is not None:
                cur_parent = arb_ids.get(var)
                if cur_parent is None:
                    ids = obs_ids.get(var)
                    cur_parent = ids[-1] if ids else None
                if cur_parent is None:
                    cur_parent = (
                        "agent:environment"
                        if any(n.id == "agent:environment" for n in nodes)
                        else parent_for_data
                    )
                cmp_parents.append(
                    _cmp_obs_node(var, cmp.current, "current", cur_parent)
                )
            if cmp.reference is not None and cmp.reference.value is not None:
                cmp_parents.append(
                    _cmp_obs_node(var, cmp.reference, "reference", history_id)
                )
            if not cmp_parents:
                cmp_parents = [history_id]

            cdetail = {
                "variable": var,
                "status": cmp.status,
                "direction": cmp.direction.value,
                "reference_window": cmp.reference_window,
                "data_sufficiency": cmp.data_sufficiency.value,
                "confidence": cmp.confidence.value,
                "engine_version": cmp.engine_version,
                "disclaimer": cmp.disclaimer,
            }
            if cmp.current is not None and cmp.current.value is not None:
                cdetail["current_value"] = f"{cmp.current.value}"
            if cmp.reference is not None and cmp.reference.value is not None:
                cdetail["reference_value"] = f"{cmp.reference.value}"
            if cmp.relative_change_pct is not None:
                cdetail["relative_change_pct"] = f"{cmp.relative_change_pct}"
            add(
                ProvNode(
                    id=f"comparison:{var}",
                    kind=ProvNodeKind.ENVIRONMENTAL_COMPARISON,
                    label=f"{var} current vs ORCA-computed reference",
                    value=(
                        cmp.absolute_change
                        if cmp.absolute_change is not None
                        else cmp.status
                    ),
                    unit=(
                        cmp.current.unit
                        if cmp.current is not None and cmp.absolute_change is not None
                        else None
                    ),
                    detail=cdetail,
                ),
                *dict.fromkeys(cmp_parents),
            )

    # ---- environmental stability / coverage (Phase 9 Step 6; never feeds safety) ----
    if stability is not None and (
        stability.sst is not None or stability.chlorophyll_a is not None
    ):
        _STAB = ProvNodeKind.ENVIRONMENTAL_STABILITY
        hist_parent = (
            "agent:environment_history"
            if any(n.id == "agent:environment_history" for n in nodes)
            else parent_for_data
        )
        stab_agent = add(
            ProvNode(
                id="agent:environment_stability", kind=_AGENT_RESULT,
                label=(
                    "environmental stability profile (ORCA-derived, bounded-window "
                    "dispersion & coverage)"
                ),
                value=stability.window or "bounded window",
                source="orca-environmental-stability-engine",
            ),
            hist_parent,
        )

        stab_prof_ids: list[str] = []
        overall_bits: list[str] = []
        for var, prof in (
            ("sea_surface_temperature", stability.sst),
            ("chlorophyll_a", stability.chlorophyll_a),
        ):
            if prof is None:
                continue
            overall_bits.append(f"{var}={prof.status}")
            series_id = add(
                ProvNode(
                    id=f"stability_series:{var}", kind=ProvNodeKind.OBSERVATION,
                    label=f"{var} accepted historical series (bounded window)",
                    value=prof.observation_count, unit="observations",
                    detail={
                        "window": prof.window,
                        "coverage": prof.coverage or "",
                        "status": prof.status,
                    },
                ),
                stab_agent,
            )
            sdetail: dict[str, str] = {
                "variable": var,
                "status": prof.status,
                "window": prof.window,
                "observation_count": f"{prof.observation_count}",
                "engine_version": stability.engine_version,
                "disclaimer": stability.disclaimer,
            }
            for k, v in (
                ("minimum", prof.minimum), ("maximum", prof.maximum),
                ("range", prof.range), ("q1", prof.q1), ("median", prof.median),
                ("q3", prof.q3), ("iqr", prof.iqr),
            ):
                if v is not None:
                    sdetail[k] = f"{v}"
            if prof.coverage:
                sdetail["coverage"] = prof.coverage
            if prof.gaps:
                sdetail["gaps"] = " | ".join(prof.gaps)
            stab_prof_ids.append(
                add(
                    ProvNode(
                        id=f"stability:{var}", kind=_STAB,
                        label=f"{var} bounded-window dispersion & coverage",
                        value=(prof.median if prof.median is not None else prof.status),
                        unit=(prof.unit or None) if prof.median is not None else None,
                        detail=sdetail,
                    ),
                    series_id,
                )
            )

        add(
            ProvNode(
                id="assessment:environment_stability", kind=_STAB,
                label="environmental stability / coverage assessment (ORCA-derived)",
                value="; ".join(overall_bits) if overall_bits else "unavailable",
                detail={
                    "window": stability.window,
                    "engine_version": stability.engine_version,
                    "disclaimer": stability.disclaimer,
                    "limitations": " | ".join(stability.limitations),
                },
            ),
            stab_agent, *dict.fromkeys(stab_prof_ids),
        )

    # ---- chlorophyll-a pixel-neighbourhood representativeness (Phase 9 Step 7; never feeds safety) ----
    if neighbourhood is not None:
        _NB = ProvNodeKind.ENVIRONMENTAL_NEIGHBOURHOOD
        # parent: the EXISTING central chlorophyll-a observation this profile qualifies.
        chl_parent = None
        for cand in ("comparison:chlorophyll_a", "productivity"):
            if any(n.id == cand for n in nodes):
                chl_parent = cand
                break
        if chl_parent is None:
            chl_parent = arb_ids.get("chlorophyll_a")
        if chl_parent is None:
            ids = obs_ids.get("chlorophyll_a")
            chl_parent = ids[-1] if ids else parent_for_data

        nb_agent = add(
            ProvNode(
                id="agent:environment_neighbourhood", kind=_AGENT_RESULT,
                label=(
                    "chlorophyll-a pixel-neighbourhood profile (ORCA-derived, one "
                    "isolated ERDDAP box request)"
                ),
                value=neighbourhood.status,
                source=(
                    f"noaa-coastwatch-erddap:{neighbourhood.dataset}"
                    if neighbourhood.dataset
                    else "noaa-coastwatch-erddap"
                ),
            ),
            chl_parent,
        )

        count_id = add(
            ProvNode(
                id="neighbourhood_pixels", kind=ProvNodeKind.OBSERVATION,
                label="valid chlorophyll-a pixels in the neighbourhood box",
                value=neighbourhood.cells_with_data, unit="pixels",
                detail={
                    "box": neighbourhood.box,
                    "half_width_deg": f"{neighbourhood.half_width_deg}",
                    "cells_total": f"{neighbourhood.cells_total}",
                    "cells_with_data": f"{neighbourhood.cells_with_data}",
                    "composite_date": neighbourhood.composite_date or "",
                    "coverage": (
                        "" if neighbourhood.coverage is None
                        else f"{neighbourhood.coverage}"
                    ),
                    "status": neighbourhood.status,
                },
            ),
            nb_agent,
        )

        ndetail: dict[str, str] = {
            "variable": neighbourhood.variable,
            "status": neighbourhood.status,
            "unit": neighbourhood.unit,
            "dataset": neighbourhood.dataset,
            "box": neighbourhood.box,
            "half_width_deg": f"{neighbourhood.half_width_deg}",
            "composite_date": neighbourhood.composite_date or "",
            "cells_total": f"{neighbourhood.cells_total}",
            "cells_with_data": f"{neighbourhood.cells_with_data}",
            "central_pixel_vs_median": neighbourhood.central_pixel_vs_median,
            "engine_version": neighbourhood.engine_version,
            "disclaimer": neighbourhood.disclaimer,
        }
        for k, v in (
            ("coverage", neighbourhood.coverage),
            ("nearest_valid_pixel_km", neighbourhood.nearest_valid_pixel_km),
            ("minimum", neighbourhood.minimum), ("maximum", neighbourhood.maximum),
            ("range", neighbourhood.range), ("q1", neighbourhood.q1),
            ("median", neighbourhood.median), ("q3", neighbourhood.q3),
            ("iqr", neighbourhood.iqr), ("central_value", neighbourhood.central_value),
        ):
            if v is not None:
                ndetail[k] = f"{v}"
        if neighbourhood.limitations:
            ndetail["limitations"] = " | ".join(neighbourhood.limitations)

        stats_id = add(
            ProvNode(
                id="neighbourhood_stats", kind=_NB,
                label="chlorophyll-a neighbourhood dispersion statistics",
                value=(
                    neighbourhood.median
                    if neighbourhood.median is not None
                    else neighbourhood.status
                ),
                unit=(
                    (neighbourhood.unit or None)
                    if neighbourhood.median is not None
                    else None
                ),
                detail=ndetail,
            ),
            count_id,
        )

        add(
            ProvNode(
                id="assessment:environment_neighbourhood", kind=_NB,
                label=(
                    "chlorophyll-a pixel-neighbourhood representativeness "
                    "assessment (ORCA-derived)"
                ),
                value=neighbourhood.central_pixel_vs_median,
                detail={
                    "status": neighbourhood.status,
                    "central_pixel_vs_median": neighbourhood.central_pixel_vs_median,
                    "engine_version": neighbourhood.engine_version,
                    "disclaimer": neighbourhood.disclaimer,
                    "limitations": " | ".join(neighbourhood.limitations),
                },
            ),
            nb_agent, count_id, stats_id,
        )

    # ---- environmental evidence / reproducibility (Phase 9 Step 5; never feeds safety) ----
    if evidence is not None and evidence.items:
        ev_agent = add(
            ProvNode(
                id="agent:environment_evidence", kind=_AGENT_RESULT,
                label="environmental evidence assessment (ORCA-derived, reproducibility)",
                value=evidence.status,
                source="orca-environmental-evidence-engine",
            ),
            parent_for_data,
        )

        def _ev_parent(var: str) -> str:
            for cand in (f"comparison:{var}", "productivity"):
                if any(n.id == cand for n in nodes):
                    return cand
            if var in arb_ids:
                return arb_ids[var]
            ids = obs_ids.get(var)
            if ids:
                return ids[-1]
            return ev_agent

        item_ids: list[str] = []
        for it in evidence.items:
            iid = f"evidence_item:{it.variable}:{it.observation_kind}"
            idetail = {
                "variable": it.variable,
                "observation_kind": it.observation_kind,
                "reproducibility_status": it.reproducibility_status,
                "validity": it.validity or "",
                "age": it.age,
                "evidence_tier": it.evidence_tier or "",
                "source_status": it.source_status,
                "source": it.source or "",
                "dataset": it.dataset or "",
                "observation_time": it.observation_time or "",
            }
            if it.spatial_distance_km is not None:
                idetail["spatial_distance_km"] = f"{it.spatial_distance_km}"
            item_ids.append(
                add(
                    ProvNode(
                        id=iid, kind=ProvNodeKind.ENVIRONMENTAL_EVIDENCE,
                        label=f"{it.variable} ({it.observation_kind}) evidence record",
                        value=it.value if it.value is not None else it.reproducibility_status,
                        unit=it.unit or None,
                        source=it.source,
                        validity=it.validity,
                        detail=idetail,
                    ),
                    _ev_parent(it.variable) if it.observation_kind == "current" else ev_agent,
                )
            )

        adetail = {
            "status": evidence.status,
            "engine_version": evidence.engine_version,
            "disclaimer": evidence.disclaimer,
        }
        if evidence.summary:
            adetail["summary"] = evidence.summary
        if evidence.optical_water_hint:
            adetail["optical_water_hint"] = evidence.optical_water_hint
        add(
            ProvNode(
                id="assessment:environment_evidence",
                kind=ProvNodeKind.ENVIRONMENTAL_EVIDENCE,
                label="environmental evidence / reproducibility assessment (ORCA-derived)",
                value=evidence.status,
                detail=adetail,
            ),
            ev_agent, *dict.fromkeys(item_ids),
        )

    # ---- official marine advisory (A8): retrieval -> temporal validation ->
    # location applicability, separate from the generic obs/validity nodes
    # above so the area-matching + severity classification are explicit and
    # traceable back to the query, even when the advisory could not be
    # matched/fetched at all. ----
    if advisory is not None:
        adv_parent = None
        ids = obs_ids.get("advisory_level")
        if ids:
            adv_parent = f"validity:advisory_level:{ids[-1].rsplit(':', 1)[-1]}"
            if not any(n.id == adv_parent for n in nodes):
                adv_parent = ids[-1]
        if adv_parent is None:
            adv_parent = advisory_agent_id or parent_for_data
        add(
            ProvNode(
                id="advisory:assessment", kind=ProvNodeKind.ADVISORY,
                label=f"official marine advisory applicability ({advisory.area})",
                value=advisory.severity.value,
                source=advisory.source,
                timestamp=advisory.retrieved_at,
                detail={
                    "area": advisory.area,
                    "availability": advisory.availability.value,
                    "warning_text": advisory.warning_text or "(none)",
                    "issued_at": advisory.issued_at.isoformat() if advisory.issued_at else "",
                    "valid_from": advisory.valid_from.isoformat() if advisory.valid_from else "",
                    "valid_until": advisory.valid_until.isoformat() if advisory.valid_until else "",
                    "source_url": advisory.source_url,
                    "raw_id": advisory.raw_id or "",
                },
            ),
            adv_parent,
        )

    # ---- risk ----
    risk_id = None
    if risk is not None:
        risk_id = add(
            ProvNode(
                id="risk", kind=ProvNodeKind.RISK, label="deterministic risk",
                value=risk.overall_score, unit="score",
                detail={
                    "risk_level": risk.risk_level.value,
                    "data_sufficiency": risk.data_sufficiency.value,
                    "calculation_version": risk.calculation_version,
                    "config_version": risk.config_version,
                },
            ),
            *[arb_ids.get(v, parent_for_data) for v in ("wave_height", "wind_speed", "weather_code", "mean_sea_level_pressure")],
        )
        for f in risk.factors:
            fnode = ProvNode(
                id=f"risk_factor:{f.name}", kind=ProvNodeKind.RISK_FACTOR,
                label=f"risk factor {f.name}",
                value=f.contribution if f.contribution is not None else f.status.value,
                unit="points" if f.contribution is not None else None,
                signal_kind=f.signal_kind.value if hasattr(f.signal_kind, "value") else str(f.signal_kind),
                detail={
                    "status": f.status.value,
                    "input_value": "" if f.input_value is None else f"{f.input_value}",
                    "band": f.band or "",
                    "required_for_safety": str(f.required_for_safety),
                },
            )
            add(fnode, risk_id)

    # ---- policy + decision ----
    policy_id = None
    if safety is not None:
        policy_id = add(
            ProvNode(
                id="policy", kind=ProvNodeKind.POLICY, label="Policy & Safety Guard",
                value=safety.status.value,
                detail={
                    "triggered_rules": ",".join(safety.triggered_rules),
                    "guard_version": safety.guard_version,
                    "hard_geofence_ids": ",".join(safety.hard_geofence_ids),
                },
            ),
            *(x for x in [risk_id] if x),
        )
    if decision is not None:
        add(
            ProvNode(
                id="decision", kind=ProvNodeKind.DECISION, label="Decision Engine",
                value=decision.status.value,
                detail={
                    "routing_allowed": str(decision.routing_allowed),
                    "decision_version": decision.decision_version,
                    "reasons": " | ".join(decision.reasons[:4]),
                },
            ),
            *(x for x in [policy_id] if x),
        )

    # ---- route ----
    if route is not None:
        parents = ["decision"] if decision is not None else [parent_for_data]
        add(
            ProvNode(
                id="route", kind=ProvNodeKind.ROUTE, label="Route Agent / A*",
                value=route.status.value,
                detail={"algorithm": route.algorithm, "version": route.algorithm_version,
                        "reasons": " | ".join(route.reasons[:3])},
            ),
            *parents,
        )
        if route.status is RouteStatus.ROUTE_FOUND:
            if route.total_distance_m is not None:
                add(ProvNode(id="route:distance", kind=ProvNodeKind.ROUTE,
                             label="route distance (approx)", value=round(route.total_distance_m, 1),
                             unit="m"), "route")
            if route.node_count is not None:
                add(ProvNode(id="route:waypoints", kind=ProvNodeKind.ROUTE,
                             label="route waypoints", value=route.node_count), "route")
            if route.grid_path_cost is not None:
                add(ProvNode(id="route:grid_cost", kind=ProvNodeKind.ROUTE,
                             label="A* grid path cost", value=route.grid_path_cost), "route")

    # ---- official INCOIS PFZ reference (B7): retrieval -> spatial match ->
    # map/reference presentation. Deliberately parented directly off the query
    # / intent, NEVER off risk/policy/decision - PFZ is a fishing-potential
    # reference only and must stay out of the safety provenance chain. ----
    if pfz is not None:
        pfz_agent = add(
            ProvNode(
                id="agent:pfz", kind=_AGENT_RESULT,
                label="official INCOIS PFZ reference retrieval",
                value=pfz.availability.value,
                source=pfz.source,
            ),
            parent_for_data,
        )
        detail = {
            "availability": pfz.availability.value,
            "area_matched": pfz.area_matched or "",
            "zone_count": str(pfz.zone_count),
            "issued_at": pfz.issued_at or "",
            "source_url": pfz.source_url,
        }
        if pfz.nearest_landing_centre is not None:
            lc = pfz.nearest_landing_centre
            detail.update(
                {
                    "nearest_landing_centre": lc.name,
                    "nearest_landing_centre_distance_km": str(lc.distance_km),
                    "nearest_landing_centre_direction": lc.direction,
                }
            )
        add(
            ProvNode(
                id="pfz:spatial_match", kind=ProvNodeKind.PFZ_REFERENCE,
                label="INCOIS PFZ spatial match (fishing-potential reference only)",
                value=pfz.zone_count,
                unit="zones",
                detail=detail,
            ),
            pfz_agent,
        )

    return ProvenanceGraph(root_id="query", nodes=tuple(nodes), edges=tuple(edges))
