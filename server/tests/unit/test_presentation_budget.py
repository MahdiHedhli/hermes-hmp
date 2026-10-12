"""Cross-phase work ceilings, no files/credentials/processes."""

import pytest

from hmp_plugin.presentation_budget import PresentationBudgetError, PresentationWorkLedger


def ledger():
    return PresentationWorkLedger(clock=lambda: 1.0, deadline=2.0)


def test_phases_share_nonresetting_counts_and_snapshot_is_copy():
    work = ledger()
    work.begin_file()
    work.charge_read_bytes(100)
    work.begin_yaml()
    work.charge_yaml_node()
    work.charge_scan()
    work.charge_hash_bytes(20)
    work.charge_unit()
    result = work.snapshot()
    assert result["read_bytes"] == 100 and result["yaml_nodes"] == 1
    assert result["hash_bytes"] == 20 and result["raster_units"] == 1
    result["read_bytes"] = 0
    assert work.snapshot()["read_bytes"] == 100


@pytest.mark.parametrize("phase", ["begin_file", "begin_yaml", "charge_scan"])
def test_repeated_phase_refuses_and_poison_survives_other_phase(phase):
    work = ledger()
    getattr(work, phase)()
    with pytest.raises(PresentationBudgetError):
        getattr(work, phase)()
    with pytest.raises(PresentationBudgetError):
        work.charge_read_bytes(1)


def test_exhausted_yaml_credit_cannot_be_reset_by_raster_phase():
    work = ledger()
    work.begin_yaml()
    for _ in range(256):
        work.charge_yaml_node()
    with pytest.raises(PresentationBudgetError):
        work.charge_yaml_node()
    with pytest.raises(PresentationBudgetError):
        work.charge_scan()


def test_expiry_is_permanent_even_if_clock_moves_back():
    now = [1.0]
    work = PresentationWorkLedger(clock=lambda: now[0], deadline=2.0)
    work.begin_file()
    now[0] = 2.0
    with pytest.raises(PresentationBudgetError):
        work.begin_yaml()
    now[0] = 1.0
    with pytest.raises(PresentationBudgetError):
        work.charge_read_bytes(1)


def parent_counts():
    return {
        "read_bytes": 0,
        "hash_bytes": 0,
        "opens": 3,
        "metadata": 12,
        "path_bytes": 30,
        "yaml_nodes": 0,
        "yaml_tokens": 0,
        "raster_units": 0,
    }


def test_parent_seed_is_copied_and_spends_existing_open_limit():
    counts = parent_counts()
    work = PresentationWorkLedger(
        clock=lambda: 1.0, deadline=2.0, parent_counts=counts, parent_home="/srv/hermes"
    )
    counts["opens"] = 0
    assert work.snapshot()["opens"] == 3
    for _ in range(77):
        work.charge_open()
    assert work.snapshot()["opens"] == 80
    with pytest.raises(PresentationBudgetError):
        work.charge_open()


@pytest.mark.parametrize(
    "key,value",
    [
        ("opens", True),
        ("opens", 2),
        ("opens", 81),
        ("metadata", 11),
        ("path_bytes", 29),
        ("read_bytes", 1),
        ("yaml_tokens", 1),
    ],
)
def test_malformed_or_understated_parent_seed_refuses(key, value):
    counts = parent_counts()
    counts[key] = value
    with pytest.raises(PresentationBudgetError):
        PresentationWorkLedger(
            clock=lambda: 1.0, deadline=2.0, parent_counts=counts, parent_home="/srv/hermes"
        )


def test_parent_phase_cannot_run_again_after_construction_seed():
    work = PresentationWorkLedger(
        clock=lambda: 1.0, deadline=2.0, parent_counts=parent_counts(), parent_home="/srv/hermes"
    )
    with pytest.raises(PresentationBudgetError):
        work.begin_parent_policy()


def test_missing_extra_and_invalid_parent_geometry_are_refused():
    for home in ("/", "/srv//hermes", "/srv/../hermes", "/srv/hermes/", "relative"):
        with pytest.raises(PresentationBudgetError):
            PresentationWorkLedger.validate_parent_counts(home, parent_counts())
    for key in ("opens", "hash_bytes", "yaml_tokens"):
        counts = parent_counts()
        counts.pop(key)
        with pytest.raises(PresentationBudgetError):
            PresentationWorkLedger.validate_parent_counts("/srv/hermes", counts)
    counts = parent_counts()
    counts["unknown"] = 0
    with pytest.raises(PresentationBudgetError):
        PresentationWorkLedger.validate_parent_counts("/srv/hermes", counts)
