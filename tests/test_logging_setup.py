import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from pc_checkup.logging_setup import (
    DEBUG_VARIABLE,
    HANDLER_MARK,
    default_log_path,
    setup_logging,
)


@pytest.fixture(autouse=True)
def clean_package_logger() -> Iterator[None]:
    """Leave the package logger as it was found, so no test leaks handlers into another."""
    logger = logging.getLogger("pc_checkup")
    level = logger.level
    yield
    for handler in [h for h in logger.handlers if getattr(h, HANDLER_MARK, False)]:
        logger.removeHandler(handler)
        handler.close()
    logger.setLevel(level)


def marked_handlers() -> list[logging.Handler]:
    return [h for h in logging.getLogger("pc_checkup").handlers if getattr(h, HANDLER_MARK, False)]


def flush() -> None:
    for handler in marked_handlers():
        handler.flush()


def test_messages_go_to_the_file(tmp_path: Path) -> None:
    path = tmp_path / "checkup.log"
    assert setup_logging(path) == path
    logging.getLogger("pc_checkup.something").info("hello from the test")
    flush()
    text = path.read_text(encoding="utf-8")
    assert "hello from the test" in text
    assert "INFO pc_checkup.something" in text


def test_a_traceback_is_written_to_the_file(tmp_path: Path) -> None:
    path = tmp_path / "checkup.log"
    setup_logging(path)
    try:
        raise ValueError("boom")
    except ValueError:
        logging.getLogger("pc_checkup.x").exception("something failed")
    flush()
    text = path.read_text(encoding="utf-8")
    assert "something failed" in text
    assert "Traceback" in text
    assert "ValueError: boom" in text


def test_calling_it_twice_keeps_a_single_handler(tmp_path: Path) -> None:
    setup_logging(tmp_path / "a.log")
    setup_logging(tmp_path / "b.log")
    assert len(marked_handlers()) == 1


def test_creates_the_missing_folder(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "checkup.log"
    assert setup_logging(path) == path
    assert path.parent.is_dir()


def test_an_unusable_path_returns_none_but_still_installs_a_handler(tmp_path: Path) -> None:
    blocker = tmp_path / "blocker"
    blocker.write_text("a file, not a folder")
    assert setup_logging(blocker / "checkup.log") is None
    assert len(marked_handlers()) == 1
    logging.getLogger("pc_checkup.x").error("must not crash")


def test_level_is_info_by_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(DEBUG_VARIABLE, raising=False)
    setup_logging(tmp_path / "checkup.log")
    assert logging.getLogger("pc_checkup").level == logging.INFO


def test_the_debug_variable_turns_on_debug(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(DEBUG_VARIABLE, "1")
    setup_logging(tmp_path / "checkup.log")
    assert logging.getLogger("pc_checkup").level == logging.DEBUG


def test_default_path_is_next_to_the_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert default_log_path() == tmp_path / "pc_checkup" / "checkup.log"
