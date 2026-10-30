import subprocess
from pathlib import Path
from typing import Any

import pytest

from pc_checkup.actions import command
from pc_checkup.actions.command import decode_output, run_tool, system32


def test_system32_uses_the_windows_folder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SystemRoot", r"C:\Windows")
    assert Path(system32("sfc.exe")) == Path(r"C:\Windows\System32\sfc.exe")


def test_utf16_output_with_nulls_is_decoded() -> None:
    data = "Verificação concluída".encode("utf-16-le")
    assert b"\x00" in data
    assert decode_output(data) == "Verificação concluída"


def test_console_output_is_decoded_with_the_console_code_page(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(command, "_console_encoding", lambda: "cp850")
    assert decode_output("Proteção".encode("cp850")) == "Proteção"


def test_unknown_code_page_falls_back_without_crashing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(command, "_console_encoding", lambda: "not-a-codec")
    assert decode_output(b"plain ascii") == "plain ascii"


def test_undecodable_bytes_never_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(command, "_console_encoding", lambda: "utf-8")
    assert "\ufffd" in decode_output(b"\xff\xfe\xfa")


def fake_run(returncode: int, calls: list[tuple[list[str], dict[str, Any]]]) -> Any:
    def run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append((cmd, kwargs))
        return subprocess.CompletedProcess(cmd, returncode, stdout=b"out", stderr=b"")

    return run


def test_run_tool_uses_no_shell_and_the_given_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[list[str], dict[str, Any]]] = []
    monkeypatch.setattr(subprocess, "run", fake_run(0, calls))
    assert run_tool(["tool.exe", "/x"], timeout=99) == 0
    cmd, kwargs = calls[0]
    assert cmd == ["tool.exe", "/x"]
    assert kwargs["timeout"] == 99
    assert "shell" not in kwargs


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(0, 0), (3010, 3010), (-2146498529, 0x800F081F), (0x800F081F, 0x800F081F)],
)
def test_exit_codes_are_normalized_to_unsigned(
    monkeypatch: pytest.MonkeyPatch, raw: int, expected: int
) -> None:
    monkeypatch.setattr(subprocess, "run", fake_run(raw, []))
    assert run_tool(["tool.exe"], timeout=1) == expected


def test_timeout_and_missing_tool_are_left_to_the_caller(monkeypatch: pytest.MonkeyPatch) -> None:
    def timeout(cmd: list[str], **kwargs: Any) -> None:
        raise subprocess.TimeoutExpired(cmd, 1)

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(subprocess.TimeoutExpired):
        run_tool(["tool.exe"], timeout=1)

    def missing(cmd: list[str], **kwargs: Any) -> None:
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", missing)
    with pytest.raises(OSError):
        run_tool(["tool.exe"], timeout=1)
