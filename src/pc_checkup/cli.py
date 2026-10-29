"""Entry point for the `checkup` command: admin check, then the menu."""

from collections.abc import Callable
from pathlib import Path

from pc_checkup.admin import is_admin, relaunch_elevated
from pc_checkup.config import load_language
from pc_checkup.menu import Menu
from pc_checkup.messages import get_message


def main(
    is_admin_fn: Callable[[], bool] = is_admin,
    relaunch_fn: Callable[[], bool] = relaunch_elevated,
    input_fn: Callable[[str], str] = input,
    print_fn: Callable[[str], None] = print,
    config_path: Path | None = None,
) -> int:
    language = load_language(config_path)

    if not is_admin_fn():
        if relaunch_fn():
            return 0
        print_fn(get_message("admin.declined", language))
        input_fn(get_message("app.press_enter", language))
        return 1

    menu = Menu(language, input_fn, print_fn, config_path)
    menu.run()
    # The elevated window closes when the program ends, so wait before closing.
    input_fn(get_message("app.press_enter", menu.language))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
