from dataclasses import replace
from pathlib import Path

from pc_checkup.interpreter import interpret_ssd, trusted_readings
from pc_checkup.models import DiskInfo, Level, Report, SsdSnapshot
from pc_checkup.sources.ssd import parse_disks

FIXTURES = Path(__file__).parent / "fixtures"

GOOD_DISK = DiskInfo(
    device_id="1",
    name="Sample NVMe",
    media_type="SSD",
    bus_type="NVMe",
    health="Healthy",
    size_bytes=512_110_190_592,
    wear_percent=7,
    temperature_c=41,
    power_on_hours=1200,
    read_errors_uncorrected=0,
    write_errors_uncorrected=0,
)


def snapshot(*disks: DiskInfo) -> SsdSnapshot:
    return SsdSnapshot(disks=tuple(disks))


def texts(report: Report) -> list[str]:
    return [line.text for line in report.friendly]


def real_disks(name: str) -> tuple[DiskInfo, ...]:
    return parse_disks((FIXTURES / name).read_text(encoding="utf-8"))


def test_good_disk_with_all_readings() -> None:
    report = interpret_ssd(snapshot(GOOD_DISK), "en")
    lines = texts(report)
    assert lines[0] == "Disk 1: Sample NVMe (SSD, 512 GB, NVMe)"
    assert "Windows reports this disk as healthy." in lines
    assert "About 93% of the drive's life remains." in lines
    assert "Temperature: 41 °C." in lines
    assert "Powered on for about 1200 hours (50 days)." in lines
    assert "No uncorrected read or write errors." in lines
    assert lines[-1] == "Result: the disk looks fine."
    assert report.friendly[-1].level is Level.OK
    assert report.technical == ()


def test_real_raid_disk_without_admin_is_limited() -> None:
    report = interpret_ssd(snapshot(*real_disks("ssd_real_no_counters.json")), "en")
    lines = texts(report)
    assert lines[0] == "Disk 0: ETOPSO SSD 256GB (SSD, 256 GB, RAID)"
    assert "Windows reports this disk as healthy." in lines
    unreadable = next(line for line in lines if line.startswith("Could not read"))
    assert "wear, temperature, hours of use, read errors, write errors" in unreadable
    assert lines[-1].startswith("Result: Windows reports the disk as healthy, but")


def test_real_raid_disk_with_admin_placeholder_zeros_are_not_trusted() -> None:
    (disk,) = real_disks("ssd_real_admin.json")
    assert disk.wear_percent == 0
    assert disk.temperature_c == 0
    readings = trusted_readings(disk)
    assert readings.wear is None
    assert readings.temperature is None
    lines = texts(interpret_ssd(snapshot(disk), "en"))
    assert not any("life remains" in line for line in lines)
    assert not any(line.startswith("Temperature") for line in lines)
    assert lines[-1].startswith("Result: Windows reports the disk as healthy, but")


def test_wear_is_kept_when_temperature_is_only_missing() -> None:
    disk = replace(GOOD_DISK, temperature_c=None)
    assert trusted_readings(disk).wear == 7


def test_aging_disk_is_a_warning() -> None:
    report = interpret_ssd(snapshot(replace(GOOD_DISK, wear_percent=30)), "en")
    lines = texts(report)
    assert any("About 70% of the drive's life remains. It is aging" in line for line in lines)
    assert lines[-1].startswith("Result: worth keeping an eye on")


def test_nearly_worn_out_disk_needs_attention() -> None:
    report = interpret_ssd(snapshot(replace(GOOD_DISK, wear_percent=95)), "en")
    wear = next(line for line in report.friendly if "life remains" in line.text)
    assert wear.level is Level.ERROR
    assert "Only about 5%" in wear.text
    assert report.friendly[-1].text.startswith("Result: the disk needs attention")


def test_hot_disk_is_a_warning() -> None:
    report = interpret_ssd(snapshot(replace(GOOD_DISK, temperature_c=75)), "en")
    assert "Temperature: 75 °C, which is high. Check ventilation and dust." in texts(report)
    assert texts(report)[-1].startswith("Result: worth keeping an eye on")


def test_uncorrected_errors_need_attention() -> None:
    disk = replace(GOOD_DISK, read_errors_uncorrected=2, write_errors_uncorrected=3)
    report = interpret_ssd(snapshot(disk), "en")
    errors = next(line for line in report.friendly if "could not be corrected" in line.text)
    assert "5 read or write errors" in errors.text
    assert errors.level is Level.ERROR
    assert report.friendly[-1].text.startswith("Result: the disk needs attention")


def test_unhealthy_disk_is_red_and_needs_attention() -> None:
    report = interpret_ssd(snapshot(replace(GOOD_DISK, health="Unhealthy")), "en")
    health = report.friendly[1]
    assert health.level is Level.ERROR
    assert "unhealthy" in health.text
    assert texts(report)[-1].startswith("Result: the disk needs attention")


def test_warning_health_is_a_warning() -> None:
    report = interpret_ssd(snapshot(replace(GOOD_DISK, health="Warning")), "en")
    assert texts(report)[-1].startswith("Result: worth keeping an eye on")


def test_unknown_health_uses_generic_message() -> None:
    report = interpret_ssd(snapshot(replace(GOOD_DISK, health="Weird")), "en")
    assert "Windows could not determine the health of this disk." in texts(report)
    assert texts(report)[-1].startswith("Result: worth keeping an eye on")


def test_missing_size_does_not_crash() -> None:
    report = interpret_ssd(snapshot(replace(GOOD_DISK, size_bytes=None)), "en")
    assert texts(report)[0] == "Disk 1: Sample NVMe (SSD, ? GB, NVMe)"


def test_no_disks() -> None:
    assert texts(interpret_ssd(snapshot(), "en")) == ["No physical disks were found."]


def test_several_disks_are_separated_by_a_blank_line() -> None:
    other = replace(GOOD_DISK, device_id="2", name="Other")
    lines = texts(interpret_ssd(snapshot(GOOD_DISK, other), "en"))
    assert lines.count("") == 1
    assert lines.index("") < lines.index("Disk 2: Other (SSD, 512 GB, NVMe)")


def test_portuguese() -> None:
    lines = texts(interpret_ssd(snapshot(GOOD_DISK), "pt"))
    assert lines[0] == "Disco 1: Sample NVMe (SSD, 512 GB, NVMe)"
    assert "Resta cerca de 93% da vida útil do disco." in lines
    assert lines[-1] == "Resultado: o disco parece estar bem."
