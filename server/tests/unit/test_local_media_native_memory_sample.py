"""Memory sample guards/structure only: never native Hermes, HTTP or measurement."""
import copy
import importlib.util
import sys
from pathlib import Path

import pytest

from hmp_plugin.local_media_raster_structure import check_raster_structure

from .test_local_media_native_serving_driver import driver, good
from .test_s5_media_fetch import VALID_PNG

PATH = Path(__file__).resolve().parents[3] / "tools/compat/local_media_native_memory_sample.py"


def load():
    spec = importlib.util.spec_from_file_location("_memory_sample_guard_tests", PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def observation():
    active = {"baseline_rss": 50 * 1024**2, "baseline_max_rss": 60 * 1024**2,
        "max_rss": 100 * 1024**2, "rss_increment": 50 * 1024**2,
        "peak_traced": 45 * 1024**2, "settled_traced": 100000,
        "buffers_held": 4, "workers_held": 4, "fifth_status": 429, "p1_started": 4,
        "max_client_chunk": 65536, "responses": 4, "body_bytes": 32 * 1024**2,
        "cancelled_handlers": 0}
    cancelled = dict(active, responses=0, body_bytes=0, max_client_chunk=0, cancelled_handlers=4)
    return {"active": active, "cancelled": cancelled}


def test_import_does_not_import_native_or_measurement_libraries():
    before = set(sys.modules)
    module = load()
    assert callable(module.run_memory_sample)
    assert not any(name.startswith(("psutil", "hermes_state", "resource", "tracemalloc"))
                   for name in set(sys.modules) - before)


def test_maximum_png_is_exact_limit_with_valid_structure_and_same_dimensions():
    module = load()
    image = module.maximum_png(VALID_PNG)
    assert len(image) == 8 * 1024**2
    assert check_raster_structure(image) == check_raster_structure(VALID_PNG)
    assert image.endswith(VALID_PNG[-12:])
    assert image != VALID_PNG  # Structural fixture, not phone decode qualification.


@pytest.mark.parametrize("bad", [None, bytearray(VALID_PNG), b"", VALID_PNG[:-1],
                                 b"x" + VALID_PNG[1:]])
def test_bad_seed_refuses_before_constructing_image(bad):
    with pytest.raises(RuntimeError):
        load().maximum_png(bad)


def test_closed_memory_observation_accepts_both_required_cases():
    load().validate_memory_report(observation())


@pytest.mark.parametrize(("field", "bad"), [
    ("peak_traced", 96 * 1024**2 + 1), ("peak_traced", 32 * 1024**2 - 1),
    ("rss_increment", 128 * 1024**2 + 1), ("rss_increment", 1),
    ("max_rss", 0), ("baseline_rss", 0), ("baseline_max_rss", 1),
    ("buffers_held", 3), ("workers_held", 3), ("fifth_status", 200),
    ("p1_started", 5), ("max_client_chunk", 65537), ("responses", 3),
    ("body_bytes", 32 * 1024**2 - 1), ("cancelled_handlers", 4),
    ("buffers_held", True), ("peak_traced", 45.0), ("settled_traced", -1),
])
def test_changed_causal_or_limit_refuses(field, bad):
    report = observation()
    report["active"][field] = bad
    with pytest.raises(RuntimeError):
        load().validate_memory_report(report)


@pytest.mark.parametrize("mutation", ["missing_case", "extra_case", "extra_field",
                                     "cancelled_response", "cancelled_body", "no_cancellations"])
def test_missing_or_ambiguous_cases_refuse(mutation):
    report = observation()
    if mutation == "missing_case":
        report.pop("cancelled")
    elif mutation == "extra_case":
        report["retry"] = copy.deepcopy(report["active"])
    elif mutation == "extra_field":
        report["active"]["ignored"] = 1
    elif mutation == "cancelled_response":
        report["cancelled"]["responses"] = 1
    elif mutation == "cancelled_body":
        report["cancelled"]["body_bytes"] = 1
    else:
        report["cancelled"]["cancelled_handlers"] = 0
    with pytest.raises(RuntimeError):
        load().validate_memory_report(report)


def test_memory_mode_is_explicit_and_cannot_expand_normal_serving_report():
    report = good()
    native, hmp, executable = (report["native_source_hashes"], report["hmp_source_hashes"],
                               report["runtime_executable_sha256"])
    driver.validate_report(report, native, hmp, executable)
    report["native_memory_observation"] = observation()
    report["native_cache_materializations"] = 7
    report["descriptor_records_retained"] = 21
    driver.validate_report(report, native, hmp, executable, sample_memory=True)
    with pytest.raises(RuntimeError):
        driver.validate_report(report, native, hmp, executable)
    report["native_memory_observation"]["active"]["fifth_status"] = 200
    with pytest.raises(RuntimeError):
        driver.validate_report(report, native, hmp, executable, sample_memory=True)


@pytest.mark.parametrize("bad", [1, None, "memory", object()])
def test_nonboolean_mode_refuses_before_materialization(tmp_path, bad):
    empty = tmp_path / "not_created"
    with pytest.raises(RuntimeError):
        driver.run_fixture(empty, empty, "a" * 40, sample_memory=bad)
    assert not empty.exists()
