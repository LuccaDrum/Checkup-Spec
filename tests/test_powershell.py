import subprocess
from typing import Any

import pytest

from pc_checkup.sources import powershell
from pc_checkup.sources.base import SourceError


def fake_run(result: Any = None, error: Exception | None = None) -> Any:
    def run(command: list[str], **kwargs: Any) -> Any:
        assert "shell" not in kwargs
        assert kwargs["timeout"] == 5
        if error:
            raise error
        return result

    return run


def completed(stdout: bytes, code: int = 0) -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess(["powershell"], code, stdout=stdout, stderr=b"err")


def test_returns_decoded_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess, "run", fake_run(completed("﻿ação".encode())))
    assert powershell.run_powershell("x", timeout=5) == "ação"


def test_non_zero_exit_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess, "run", fake_run(completed(b"", code=1)))
    with pytest.raises(SourceError):
        powershell.run_powershell("x", timeout=5)


def test_timeout_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    error = subprocess.TimeoutExpired("powershell", 5)
    monkeypatch.setattr(subprocess, "run", fake_run(error=error))
    with pytest.raises(SourceError):
        powershell.run_powershell("x", timeout=5)


def test_missing_powershell_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess, "run", fake_run(error=FileNotFoundError()))
    with pytest.raises(SourceError):
        powershell.run_powershell("x", timeout=5)
