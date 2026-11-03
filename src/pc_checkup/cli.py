"""Entry point for the `checkup` command: admin check, then the menu."""

import argparse
import logging
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from pc_checkup.actions.ram_test import REOPEN_ARGUMENT
from pc_checkup.admin import is_admin, relaunch_elevated
from pc_checkup.config import load_language
from pc_checkup.logging_setup import setup_logging
from pc_checkup.menu import Menu
from pc_checkup.messages import get_message
from pc_checkup.models import Level
from pc_checkup.ui import Ui, supports_color

logger = logging.getLogger(__name__)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="checkup", add_help=False)
    # Internal flag used when the program reopens by itself after the RAM test restart.
    parser.add_argument(REOPEN_ARGUMENT, action="store_true", help=argparse.SUPPRESS)
    args, _unknown = parser.parse_known_args(argv)
    return args


def main(
    is_admin_fn: Callable[[], bool] = is_admin,
    relaunch_fn: Callable[[], bool] = relaunch_elevated,
    input_fn: Callable[[str], str] = input,
    print_fn: Callable[[str], None] = print,
    config_path: Path | None = None,
    color: bool | None = None,
    argv: Sequence[str] | None = None,
    setup_logging_fn: Callable[[], Path | None] = setup_logging,
) -> int:
    log_path = setup_logging_fn()
    args = parse_args(sys.argv[1:] if argv is None else argv)
    language = load_language(config_path)
    use_color = supports_color() if color is None else color
    ui = Ui(use_color)

    def wait_for_enter() -> None:
        """The elevated window closes when the program ends, so wait before closing."""
        try:
            input_fn(get_message("app.press_enter", language))
        except (KeyboardInterrupt, EOFError):
            pass

    if not is_admin_fn():
        if relaunch_fn():
            return 0
        print_fn(ui.block(get_message("admin.declined", language), Level.ERROR))
        wait_for_enter()
        return 1

    menu = Menu(language, input_fn, print_fn, config_path, color=use_color)
    code = 0
    try:
        if args.show_ram_result:
            menu.show_ram_test(allow_start=False)
        menu.run()
    except (KeyboardInterrupt, EOFError):
        print_fn("")
        print_fn(ui.block(get_message("app.interrupted", menu.language)))
    except Exception:
        # A bug must not show a traceback to a non-technical user: log it and explain.
        logger.exception("Unexpected error")
        key = "app.unexpected_error" if log_path else "app.unexpected_error_no_log"
        print_fn(ui.block(get_message(key, menu.language, path=log_path), Level.ERROR))
        code = 1
    wait_for_enter()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
