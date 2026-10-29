import pytest

from pc_checkup import admin


def test_is_admin_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admin, "_user_is_admin", lambda: 1)
    assert admin.is_admin() is True


def test_is_admin_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admin, "_user_is_admin", lambda: 0)
    assert admin.is_admin() is False


def test_is_admin_false_when_the_call_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail() -> int:
        raise OSError("boom")

    monkeypatch.setattr(admin, "_user_is_admin", fail)
    assert admin.is_admin() is False


def test_relaunch_succeeds_when_windows_returns_above_32(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str]] = []

    def fake(executable: str, params: str) -> int:
        calls.append((executable, params))
        return 42

    monkeypatch.setattr(admin, "_shell_execute_runas", fake)
    assert admin.relaunch_elevated(["--x", "a b"]) is True
    assert calls[0][1] == '-m pc_checkup --x "a b"'


def test_relaunch_fails_when_user_declines_uac(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admin, "_shell_execute_runas", lambda executable, params: 5)
    assert admin.relaunch_elevated([]) is False


def test_relaunch_fails_when_the_call_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(executable: str, params: str) -> int:
        raise OSError("boom")

    monkeypatch.setattr(admin, "_shell_execute_runas", fail)
    assert admin.relaunch_elevated([]) is False
