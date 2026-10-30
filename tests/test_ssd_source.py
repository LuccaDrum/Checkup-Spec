import json
from pathlib import Path

import pytest

from pc_checkup.sources.base import SourceError
from pc_checkup.sources.ssd import DISKS_SCRIPT, SsdSource, parse_disks

FIXTURES = Path(__file__).parent / "fixtures"

FULL_DISK = {
    "DeviceId": "1",
    "Name": "Sample NVMe",
    "MediaType": "SSD",
    "BusType": "NVMe",
    "Health": "Healthy",
    "SizeBytes": 512110190592,
    "Wear": 7,
    "Temperature": 41,
    "PowerOnHours": 1200,
    "ReadErrorsUncorrected": 0,
    "WriteErrorsUncorrected": 0,
}


def test_real_output_without_admin_has_no_counters() -> None:
    text = (FIXTURES / "ssd_real_no_counters.json").read_text(encoding="utf-8")
    (disk,) = parse_disks(text)
    assert disk.name == "ETOPSO SSD 256GB"
    assert disk.health == "Healthy"
    assert disk.bus_type == "RAID"
    assert disk.size_bytes == 256060514304
    assert disk.unreadable_fields() == (
        "wear",
        "temperature",
        "power_on_hours",
        "read_errors",
        "write_errors",
    )


def test_all_counters_are_parsed() -> None:
    (disk,) = parse_disks(json.dumps([FULL_DISK]))
    assert disk.wear_percent == 7
    assert disk.temperature_c == 41
    assert disk.power_on_hours == 1200
    assert disk.read_errors_uncorrected == 0
    assert disk.write_errors_uncorrected == 0
    assert disk.unreadable_fields() == ()


def test_a_single_object_is_accepted() -> None:
    assert len(parse_disks(json.dumps(FULL_DISK))) == 1


def test_values_that_are_not_numbers_count_as_unreadable() -> None:
    raw = {**FULL_DISK, "Wear": "n/a", "Temperature": True, "PowerOnHours": None}
    (disk,) = parse_disks(json.dumps([raw]))
    assert disk.unreadable_fields() == ("wear", "temperature", "power_on_hours")


def test_several_disks() -> None:
    assert len(parse_disks(json.dumps([FULL_DISK, {**FULL_DISK, "DeviceId": "2"}]))) == 2


@pytest.mark.parametrize("output", ["", "  \n", "[]"])
def test_no_disks(output: str) -> None:
    assert parse_disks(output) == ()


@pytest.mark.parametrize("output", ["{ not json", '[{"DeviceId": "0"}]', '"text"', "[1]"])
def test_garbage_raises_source_error(output: str) -> None:
    with pytest.raises(SourceError):
        parse_disks(output)


def test_fetch_runs_the_disks_script() -> None:
    scripts: list[str] = []

    def fake_run(script: str) -> str:
        scripts.append(script)
        return json.dumps([FULL_DISK])

    snapshot = SsdSource(run_fn=fake_run).fetch()
    assert scripts == [DISKS_SCRIPT]
    assert snapshot.disks[0].name == "Sample NVMe"
