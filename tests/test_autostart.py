import sys
from typing import Self

import pytest

from pc_checkup import autostart


class FakeKey:
    def __init__(self, registry: "FakeWinreg", path: str) -> None:
        self.registry = registry
        self.path = path

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


class FakeWinreg:
    """Stands in for the registry so tests never touch the real one."""

    HKEY_CURRENT_USER = "HKCU"
    REG_SZ = 1
    KEY_SET_VALUE = 2

    def __init__(self, key_exists: bool = True) -> None:
        self.values: dict[tuple[str, str], str] = {}
        self.key_exists = key_exists

    def CreateKey(self, root: str, path: str) -> FakeKey:
        return FakeKey(self, path)

    def OpenKey(self, root: str, path: str, reserved: int, access: int) -> FakeKey:
        if not self.key_exists:
            raise FileNotFoundError
        return FakeKey(self, path)

    def SetValueEx(self, key: FakeKey, name: str, reserved: int, kind: int, value: str) -> None:
        self.values[(key.path, name)] = value

    def DeleteValue(self, key: FakeKey, name: str) -> None:
        try:
            del self.values[(key.path, name)]
        except KeyError:
            raise FileNotFoundError from None


@pytest.fixture
def fake_registry(monkeypatch: pytest.MonkeyPatch) -> FakeWinreg:
    registry = FakeWinreg()
    monkeypatch.setattr(autostart, "winreg", registry)
    return registry


def test_build_command_runs_this_python_with_the_package_and_arguments() -> None:
    command = autostart.build_command(["--show-ram-result"])
    assert command.endswith("-m pc_checkup --show-ram-result")
    assert sys.executable in command or f'"{sys.executable}"' in command


def test_register_writes_a_runonce_value(fake_registry: FakeWinreg) -> None:
    autostart.register_after_reboot("cmd to run")
    assert fake_registry.values == {(autostart.RUN_ONCE_KEY, autostart.VALUE_NAME): "cmd to run"}


def test_unregister_removes_the_value(fake_registry: FakeWinreg) -> None:
    autostart.register_after_reboot("cmd to run")
    autostart.unregister()
    assert fake_registry.values == {}


def test_unregister_when_already_gone_is_fine(fake_registry: FakeWinreg) -> None:
    autostart.unregister()


def test_unregister_without_the_key_is_fine(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(autostart, "winreg", FakeWinreg(key_exists=False))
    autostart.unregister()
