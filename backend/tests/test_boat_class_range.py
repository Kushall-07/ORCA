"""Boat-class operating-range annotation - Phase 11."""

from __future__ import annotations

from app.models.pfz import PfzAvailability, PfzZoneRankingResult, PfzZoneRef
from app.models.vessel import BoatClass, known_classes, profile
from app.orchestration.nodes import _annotate_zone_ranges


def _zone(zone_id: str, distance_km: float) -> PfzZoneRef:
    return PfzZoneRef(id=zone_id, rank=1, latitude=13.0, longitude=75.0, distance_km=distance_km)


def _ranking(*zones: PfzZoneRef) -> PfzZoneRankingResult:
    return PfzZoneRankingResult(availability=PfzAvailability.AVAILABLE, zones=zones)


def test_no_boat_class_leaves_every_zone_unknown() -> None:
    result = _annotate_zone_ranges(_ranking(_zone("a", 10.0), _zone("b", 500.0)), None)
    assert all(z.within_safe_range is None for z in result.zones)


def test_unrecognised_boat_class_leaves_every_zone_unknown() -> None:
    result = _annotate_zone_ranges(_ranking(_zone("a", 10.0)), "not_a_real_class")
    assert result.zones[0].within_safe_range is None


def test_small_motorized_flags_far_zone_out_of_range() -> None:
    result = _annotate_zone_ranges(
        _ranking(_zone("near", 20.0), _zone("far", 200.0)),
        BoatClass.SMALL_MOTORIZED.value,
    )
    by_id = {z.id: z for z in result.zones}
    assert by_id["near"].within_safe_range is True
    assert by_id["far"].within_safe_range is False


def test_large_mechanized_has_the_widest_range() -> None:
    zone = _zone("mid", 200.0)
    small = _annotate_zone_ranges(_ranking(zone), BoatClass.SMALL_MOTORIZED.value)
    large = _annotate_zone_ranges(_ranking(zone), BoatClass.LARGE_MECHANIZED.value)
    assert small.zones[0].within_safe_range is False
    assert large.zones[0].within_safe_range is True


def test_annotation_never_reorders_or_drops_zones() -> None:
    zones = (_zone("a", 5.0), _zone("b", 500.0), _zone("c", 50.0))
    result = _annotate_zone_ranges(_ranking(*zones), BoatClass.MEDIUM_MECHANIZED.value)
    assert [z.id for z in result.zones] == ["a", "b", "c"]


def test_every_known_class_has_a_positive_range() -> None:
    for p in known_classes():
        assert p.max_range_km > 0
        assert profile(p.boat_class) == p


def test_profile_accepts_both_enum_and_string() -> None:
    assert profile(BoatClass.SMALL_MOTORIZED) == profile("small_motorized")
