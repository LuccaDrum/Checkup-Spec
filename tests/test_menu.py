import subprocess
from collections.abc import Callable, Iterator
from datetime import datetime
from pathlib import Path

from pc_checkup.actions.base import Action
from pc_checkup.actions.dism import DismAction
from pc_checkup.actions.ram_test import RamTestAction
from pc_checkup.actions.sfc import SfcAction
from pc_checkup.config import load_language
from pc_checkup.menu import CONFIRMATION_PAUSE_SECONDS, Menu
from pc_checkup.models import (
    BsodSnapshot,
    DiskInfo,
    EventKind,
    RamOutcome,
    RamSnapshot,
    RamTestResult,
    SsdSnapshot,
    SystemEvent,
)
from pc_checkup.sources.base import Source, SourceError


class FakeBsodSource(Source[BsodSnapshot]):
    def __init__(self, snapshot: BsodSnapshot | None = None, fail: bool = False) -> None:
        self._snapshot = snapshot or BsodSnapshot(days=15, events=(), dump_files=())
        self._fail = fail
        self.calls = 0

    def fetch(self) -> BsodSnapshot:
        self.calls += 1
        if self._fail:
            raise SourceError("boom")
        return self._snapshot


class FakeSsdSource(Source[SsdSnapshot]):
    def __init__(self, snapshot: SsdSnapshot | None = None, fail: bool = False) -> None:
        self._snapshot = snapshot or SsdSnapshot(disks=())
        self._fail = fail
        self.calls = 0

    def fetch(self) -> SsdSnapshot:
        self.calls += 1
        if self._fail:
            raise SourceError("boom")
        return self._snapshot


class FakeRamSource(Source[RamSnapshot]):
    def __init__(self, snapshot: RamSnapshot | None = None, fail: bool = False) -> None:
        self._snapshot = snapshot or RamSnapshot(latest=None)
        self._fail = fail
        self.calls = 0

    def fetch(self) -> RamSnapshot:
        self.calls += 1
        if self._fail:
            raise SourceError("boom")
        return self._snapshot


def safe_ram_action(tmp_path: Path) -> RamTestAction:
    """A RAM action that never opens mdsched and keeps its state in the temp folder."""
    return RamTestAction(
        schedule_fn=lambda: None,
        restart_fn=lambda comment: None,
        register_fn=lambda: None,
        unregister_fn=lambda: None,
        state_path=tmp_path / "ram_state.json",
    )


def make_menu(
    answers: list[str],
    tmp_path: Path,
    language: str = "en",
    source: Source[BsodSnapshot] | None = None,
    ssd_source: Source[SsdSnapshot] | None = None,
    ram_source: Source[RamSnapshot] | None = None,
    ram_action: RamTestAction | None = None,
    ram_source_factory: Callable[[datetime], Source[RamSnapshot]] | None = None,
    sfc_action: Action | None = None,
    dism_action: Action | None = None,
) -> tuple[Menu, list[str], Path]:
    """Build a Menu fed by `answers`; returns it with its printed lines and config path."""
    printed: list[str] = []
    remaining: Iterator[str] = iter(answers)
    config_path = tmp_path / "config.json"
    menu = Menu(
        language,
        input_fn=lambda prompt: next(remaining),
        print_fn=printed.append,
        config_path=config_path,
        bsod_source=source or FakeBsodSource(),
        ssd_source=ssd_source or FakeSsdSource(),
        ram_source=ram_source or FakeRamSource(),
        ram_action=ram_action or safe_ram_action(tmp_path),
        ram_source_factory=ram_source_factory,
        sfc_action=sfc_action or SfcAction(run_fn=lambda command, timeout: 0),
        dism_action=dism_action or DismAction(run_fn=lambda command, timeout: 0),
        sleep_fn=lambda seconds: None,
    )
    return menu, printed, config_path


def test_exit_shows_menu_and_goodbye(tmp_path: Path) -> None:
    menu, printed, _ = make_menu(["0"], tmp_path)
    menu.run()
    assert "=== PC Checkup ===" in printed
    assert "7) Settings (language)" in printed
    assert printed[-1] == "Goodbye!"


def test_invalid_input_repeats_the_prompt(tmp_path: Path) -> None:
    menu, printed, _ = make_menu(["abc", "9", "", "   ", "0"], tmp_path)
    menu.run()
    assert printed.count("That is not a valid option. Please type a number from the menu.") == 4
    assert printed[-1] == "Goodbye!"


def test_input_is_trimmed(tmp_path: Path) -> None:
    menu, printed, _ = make_menu([" 0 "], tmp_path)
    menu.run()
    assert printed[-1] == "Goodbye!"


def test_settings_switches_language_and_saves_it(tmp_path: Path) -> None:
    menu, printed, config_path = make_menu(["7", "0"], tmp_path)
    menu.run()
    assert "Language changed to English." not in printed
    assert "Idioma alterado para português." in printed
    assert menu.language == "pt"
    assert load_language(config_path) == "pt"
    assert printed[-1] == "Até logo!"


def test_settings_switches_back_to_english(tmp_path: Path) -> None:
    menu, printed, config_path = make_menu(["7", "0"], tmp_path, language="pt")
    menu.run()
    assert "Language changed to English." in printed
    assert load_language(config_path) == "en"


def crash_snapshot() -> BsodSnapshot:
    crash = SystemEvent(
        time=datetime(2026, 10, 29, 7, 43),
        kind=EventKind.BUGCHECK,
        event_id=1001,
        bugcheck_code=0x1A,
    )
    return BsodSnapshot(days=15, events=(crash,), dump_files=())


def test_option_2_shows_friendly_report_then_technical_details(tmp_path: Path) -> None:
    source = FakeBsodSource(crash_snapshot())
    menu, printed, _ = make_menu(["2", "0"], tmp_path, source=source)
    menu.run()
    assert source.calls == 1
    friendly = printed.index("Your PC crashed once in the last 15 days.")
    technical = printed.index("Technical details:")
    assert friendly < technical
    assert any("code=0x1a MEMORY_MANAGEMENT" in line for line in printed)


def test_option_2_in_portuguese(tmp_path: Path) -> None:
    source = FakeBsodSource(crash_snapshot())
    menu, printed, _ = make_menu(["2", "0"], tmp_path, language="pt", source=source)
    menu.run()
    assert "Seu PC travou uma vez nos últimos 15 dias." in printed


def test_option_2_without_problems(tmp_path: Path) -> None:
    menu, printed, _ = make_menu(["2", "0"], tmp_path)
    menu.run()
    assert any(line.startswith("Good news") for line in printed)


def test_option_2_failure_shows_friendly_message_and_keeps_running(tmp_path: Path) -> None:
    menu, printed, _ = make_menu(["2", "0"], tmp_path, source=FakeBsodSource(fail=True))
    menu.run()
    assert any("Could not read the Windows event log" in line for line in printed)
    assert printed[-1] == "Goodbye!"


def make_color_menu(answers: list[str], source: Source[BsodSnapshot]) -> tuple[Menu, list[str]]:
    printed: list[str] = []
    remaining: Iterator[str] = iter(answers)
    menu = Menu(
        "en",
        input_fn=lambda prompt: next(remaining),
        print_fn=printed.append,
        bsod_source=source,
        color=True,
        sleep_fn=lambda seconds: None,
    )
    return menu, printed


def test_color_menu_has_bold_options_and_separators() -> None:
    menu, printed = make_color_menu(["0"], FakeBsodSource())
    menu.run()
    assert "\x1b[1m2)\x1b[0m Blue screens (last 15 days)" in printed
    assert "─" in printed[1]


def test_color_menu_shows_invalid_input_in_red() -> None:
    menu, printed = make_color_menu(["abc", "0"], FakeBsodSource())
    menu.run()
    errors = [line for line in printed if line.startswith("\x1b[1;97;41m")]
    assert len(errors) == 1
    assert "not a valid option" in errors[0]


def test_color_report_has_red_headline_gray_log_and_plain_details() -> None:
    menu, printed = make_color_menu(["2", "0"], FakeBsodSource(crash_snapshot()))
    menu.run()
    text = "\n".join(printed)
    assert "\x1b[1;97;41m" in text
    assert "\x1b[30;47m" in text
    assert "\x1b[97;100m" not in text
    assert "Technical details:" in printed


def test_language_change_pauses_briefly_so_it_can_be_read(tmp_path: Path) -> None:
    pauses: list[float] = []
    answers: Iterator[str] = iter(["7", "0"])
    menu = Menu(
        "en",
        input_fn=lambda prompt: next(answers),
        print_fn=lambda text: None,
        config_path=tmp_path / "config.json",
        bsod_source=FakeBsodSource(),
        sleep_fn=pauses.append,
    )
    menu.run()
    assert pauses == [CONFIRMATION_PAUSE_SECONDS]
    assert 0 < CONFIRMATION_PAUSE_SECONDS <= 1


def test_language_change_notice_is_black_on_light_cyan(tmp_path: Path) -> None:
    menu, printed = make_color_menu(["7", "0"], FakeBsodSource())
    menu.run()
    notices = [line for line in printed if line.startswith("\x1b[30;106m")]
    assert len(notices) == 1
    assert "Idioma alterado" in notices[0]


def test_no_pause_without_a_language_change(tmp_path: Path) -> None:
    pauses: list[float] = []
    answers: Iterator[str] = iter(["2", "0"])
    menu = Menu(
        "en",
        input_fn=lambda prompt: next(answers),
        print_fn=lambda text: None,
        bsod_source=FakeBsodSource(),
        sleep_fn=pauses.append,
    )
    menu.run()
    assert pauses == []


def healthy_disk_snapshot() -> SsdSnapshot:
    disk = DiskInfo(
        device_id="0",
        name="Sample SSD",
        media_type="SSD",
        bus_type="NVMe",
        health="Healthy",
        size_bytes=256_000_000_000,
        wear_percent=5,
        temperature_c=40,
        power_on_hours=100,
        read_errors_uncorrected=0,
        write_errors_uncorrected=0,
    )
    return SsdSnapshot(disks=(disk,))


def test_option_3_shows_the_disk_report_without_technical_details(tmp_path: Path) -> None:
    source = FakeSsdSource(healthy_disk_snapshot())
    menu, printed, _ = make_menu(["3", "0"], tmp_path, ssd_source=source)
    menu.run()
    assert source.calls == 1
    assert "Reading disk information..." in printed
    assert "Disk 0: Sample SSD (SSD, 256 GB, NVMe)" in printed
    assert "Result: the disk looks fine." in printed
    assert "Technical details:" not in printed


def test_option_3_in_portuguese(tmp_path: Path) -> None:
    source = FakeSsdSource(healthy_disk_snapshot())
    menu, printed, _ = make_menu(["3", "0"], tmp_path, language="pt", ssd_source=source)
    menu.run()
    assert "Resultado: o disco parece estar bem." in printed


def test_option_3_failure_shows_friendly_message_and_keeps_running(tmp_path: Path) -> None:
    menu, printed, _ = make_menu(["3", "0"], tmp_path, ssd_source=FakeSsdSource(fail=True))
    menu.run()
    assert any("Could not read the disk information" in line for line in printed)
    assert printed[-1] == "Goodbye!"

def ram_ok_snapshot() -> RamSnapshot:
    result = RamTestResult(
        time=datetime(2026, 10, 25, 9, 12), outcome=RamOutcome.NO_ERRORS, event_id=1201
    )
    return RamSnapshot(latest=result)


def test_option_1_runs_every_check_and_puts_technical_details_last(tmp_path: Path) -> None:
    bsod, ssd, ram = (
        FakeBsodSource(crash_snapshot()),
        FakeSsdSource(healthy_disk_snapshot()),
        FakeRamSource(ram_ok_snapshot()),
    )
    menu, printed, _ = make_menu(["1", "0"], tmp_path, source=bsod, ssd_source=ssd, ram_source=ram)
    menu.run()
    assert (bsod.calls, ssd.calls, ram.calls) == (1, 1, 1)
    headings = [
        printed.index("Blue screens (last 15 days)"),
        printed.index("SSD health"),
        printed.index("RAM test"),
    ]
    assert headings == sorted(headings)
    assert "Your PC crashed once in the last 15 days." in printed
    assert "Result: the disk looks fine." in printed
    assert "The last RAM test (2026-10-25 09:12) found no errors." in printed
    technical = printed.index("Technical details:")
    assert technical > printed.index("Result: the memory looked fine in the last test.")


def test_option_1_keeps_going_when_one_section_fails(tmp_path: Path) -> None:
    ssd = FakeSsdSource(fail=True)
    ram = FakeRamSource(ram_ok_snapshot())
    menu, printed, _ = make_menu(["1", "0"], tmp_path, ssd_source=ssd, ram_source=ram)
    menu.run()
    assert any("Could not read the disk information" in line for line in printed)
    assert "The last RAM test (2026-10-25 09:12) found no errors." in printed
    assert printed[-1] == "Goodbye!"


def test_option_1_shows_the_technical_section_once_at_the_end(tmp_path: Path) -> None:
    menu, printed, _ = make_menu(["1", "0"], tmp_path)
    menu.run()
    assert printed.count("Technical details:") == 1
    assert printed.index("Technical details:") > printed.index("Result: nothing to report yet.")

class RamHarness:
    """A RAM action with a launch counter and its own state file, plus a fake result source."""

    def __init__(self, tmp_path: Path, schedule_error: Exception | None = None) -> None:
        self.scheduled = 0
        self.restarts = 0
        self.since_asked: list[datetime] = []
        self.snapshot = RamSnapshot(latest=None)
        self.fail_read = False

        def schedule() -> None:
            if schedule_error:
                raise schedule_error
            self.scheduled += 1

        def restart(comment: str) -> None:
            self.restarts += 1

        self.action = RamTestAction(
            schedule_fn=schedule,
            restart_fn=restart,
            register_fn=lambda: None,
            unregister_fn=lambda: None,
            state_path=tmp_path / "ram_state.json",
            now_fn=lambda: datetime(2026, 10, 30, 10, 15).astimezone(),
        )

    def factory(self, since: datetime) -> Source[RamSnapshot]:
        self.since_asked.append(since)
        return FakeRamSource(self.snapshot, fail=self.fail_read)


def run_ram_menu(
    answers: list[str], tmp_path: Path, harness: RamHarness, language: str = "en"
) -> list[str]:
    menu, printed, _ = make_menu(
        answers,
        tmp_path,
        language=language,
        ram_action=harness.action,
        ram_source_factory=harness.factory,
    )
    menu.run()
    return printed


def test_option_4_explains_asks_and_starts_the_test(tmp_path: Path) -> None:
    ram = RamHarness(tmp_path)
    printed = run_ram_menu(["4", "y", "0"], tmp_path, ram)
    assert ram.restarts == 1
    assert ram.action.pending_since() is not None
    assert any("Windows Memory Diagnostic checks your RAM" in line for line in printed)
    assert any("10 to 20 minutes" in line for line in printed)
    assert any("restart in 15 seconds" in line for line in printed)


def test_option_4_declined_changes_nothing(tmp_path: Path) -> None:
    ram = RamHarness(tmp_path)
    printed = run_ram_menu(["4", "n", "0"], tmp_path, ram)
    assert ram.restarts == 0
    assert ram.action.pending_since() is None
    assert "Cancelled. Nothing was changed on your PC." in printed


def test_option_4_anything_but_yes_counts_as_no(tmp_path: Path) -> None:
    ram = RamHarness(tmp_path)
    run_ram_menu(["4", "", "0"], tmp_path, ram)
    assert ram.restarts == 0


def test_option_4_accepts_portuguese_yes(tmp_path: Path) -> None:
    ram = RamHarness(tmp_path)
    printed = run_ram_menu(["4", "sim", "0"], tmp_path, ram, language="pt")
    assert ram.restarts == 1
    assert any("Diagnóstico de Memória" in line for line in printed)


def test_option_4_launch_failure_is_red_and_leaves_no_pending_test(tmp_path: Path) -> None:
    ram = RamHarness(tmp_path, schedule_error=OSError("bcdedit failed"))
    printed = run_ram_menu(["4", "y", "0"], tmp_path, ram)
    assert any("your PC was not restarted" in line for line in printed)
    assert ram.action.pending_since() is None


def test_option_4_with_a_pending_test_shows_the_new_result_and_clears_it(tmp_path: Path) -> None:
    ram = RamHarness(tmp_path)
    ram.action.run("en")
    pending = ram.action.pending_since()
    ram.snapshot = ram_ok_snapshot()
    printed = run_ram_menu(["4", "0"], tmp_path, ram)
    assert ram.since_asked == [pending]
    assert "The last RAM test (2026-10-25 09:12) found no errors." in printed
    assert ram.action.pending_since() is None
    assert ram.restarts == 1


def test_option_4_pending_without_result_says_it_has_not_run(tmp_path: Path) -> None:
    ram = RamHarness(tmp_path)
    ram.action.run("en")
    printed = run_ram_menu(["4", "n", "0"], tmp_path, ram)
    assert any("The test has not run yet" in line for line in printed)
    assert ram.action.pending_since() is not None
    assert ram.restarts == 1


def test_option_4_pending_without_result_can_start_a_new_test(tmp_path: Path) -> None:
    ram = RamHarness(tmp_path)
    ram.action.run("en")
    run_ram_menu(["4", "y", "y", "0"], tmp_path, ram)
    assert ram.restarts == 2


def test_option_4_read_failure_keeps_the_pending_test(tmp_path: Path) -> None:
    ram = RamHarness(tmp_path)
    ram.action.run("en")
    ram.fail_read = True
    printed = run_ram_menu(["4", "0"], tmp_path, ram)
    assert any("Could not read the RAM test result" in line for line in printed)
    assert ram.action.pending_since() is not None

def test_read_only_mode_without_a_pending_test_never_starts_one(tmp_path: Path) -> None:
    ram = RamHarness(tmp_path)
    menu, printed, _ = make_menu(
        [], tmp_path, ram_action=ram.action, ram_source_factory=ram.factory
    )
    menu.show_ram_test(allow_start=False)
    assert any("No RAM test is waiting for a result" in line for line in printed)
    assert (ram.scheduled, ram.restarts) == (0, 0)
    assert ram.action.pending_since() is None


def test_read_only_mode_shows_the_result_and_clears_the_record(tmp_path: Path) -> None:
    ram = RamHarness(tmp_path)
    ram.action.run("en")
    ram.snapshot = ram_ok_snapshot()
    menu, printed, _ = make_menu(
        [], tmp_path, ram_action=ram.action, ram_source_factory=ram.factory
    )
    menu.show_ram_test(allow_start=False)
    assert "The last RAM test (2026-10-25 09:12) found no errors." in printed
    assert ram.action.pending_since() is None


def test_read_only_mode_without_a_result_does_not_offer_a_new_test(tmp_path: Path) -> None:
    ram = RamHarness(tmp_path)
    ram.action.run("en")
    restarts_before = ram.restarts
    menu, printed, _ = make_menu(
        [], tmp_path, ram_action=ram.action, ram_source_factory=ram.factory
    )
    menu.show_ram_test(allow_start=False)
    assert any("The test has not run yet" in line for line in printed)
    assert ram.restarts == restarts_before
    assert ram.action.pending_since() is not None


class RepairRunner:
    """Stands in for the real tool: returns a chosen exit code and counts the runs."""

    def __init__(self, code: int = 0, error: Exception | None = None) -> None:
        self.code = code
        self.error = error
        self.runs = 0

    def __call__(self, command: list[str], timeout: int) -> int:
        self.runs += 1
        if self.error:
            raise self.error
        return self.code


def test_option_5_explains_warns_asks_and_runs_sfc(tmp_path: Path) -> None:
    runner = RepairRunner()
    menu, printed, _ = make_menu(["5", "y", "0"], tmp_path, sfc_action=SfcAction(run_fn=runner))
    menu.run()
    assert runner.runs == 1
    assert any("System File Checker (SFC) scans" in line for line in printed)
    assert any("10 to 20 minutes" in line for line in printed)
    assert any(line.startswith("SFC finished without reporting an error") for line in printed)


def test_option_5_declined_runs_nothing(tmp_path: Path) -> None:
    runner = RepairRunner()
    menu, printed, _ = make_menu(["5", "n", "0"], tmp_path, sfc_action=SfcAction(run_fn=runner))
    menu.run()
    assert runner.runs == 0
    assert "Cancelled. Nothing was changed on your PC." in printed


def test_option_5_failure_shows_the_code_and_the_log(tmp_path: Path) -> None:
    runner = RepairRunner(code=1)
    menu, printed, _ = make_menu(["5", "y", "0"], tmp_path, sfc_action=SfcAction(run_fn=runner))
    menu.run()
    assert "Exit code: 1 (hex 0x00000001)" in printed
    assert any("CBS.log" in line for line in printed)


def test_option_6_runs_dism_and_tells_when_a_restart_is_needed(tmp_path: Path) -> None:
    runner = RepairRunner(code=3010)
    menu, printed, _ = make_menu(["6", "y", "0"], tmp_path, dism_action=DismAction(run_fn=runner))
    menu.run()
    assert runner.runs == 1
    assert any("Restart the PC when you are ready" in line for line in printed)
    assert printed[-1] == "Goodbye!"


def test_option_6_in_portuguese_accepts_sim(tmp_path: Path) -> None:
    runner = RepairRunner(code=0x800F0906)
    menu, printed, _ = make_menu(
        ["6", "sim", "0"], tmp_path, language="pt", dism_action=DismAction(run_fn=runner)
    )
    menu.run()
    assert runner.runs == 1
    assert any("não conseguiu baixar" in line for line in printed)


def test_a_repair_timeout_is_shown_and_the_menu_keeps_running(tmp_path: Path) -> None:
    runner = RepairRunner(error=subprocess.TimeoutExpired("dism", 1))
    menu, printed, _ = make_menu(["6", "y", "0"], tmp_path, dism_action=DismAction(run_fn=runner))
    menu.run()
    assert any("took too long" in line for line in printed)
    assert printed[-1] == "Goodbye!"


def test_repairs_are_never_started_without_confirmation(tmp_path: Path) -> None:
    sfc, dism = RepairRunner(), RepairRunner()
    menu, _, _ = make_menu(
        ["5", "", "6", "maybe", "0"],
        tmp_path,
        sfc_action=SfcAction(run_fn=sfc),
        dism_action=DismAction(run_fn=dism),
    )
    menu.run()
    assert (sfc.runs, dism.runs) == (0, 0)