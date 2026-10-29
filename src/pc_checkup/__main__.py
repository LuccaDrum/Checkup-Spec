"""Allows `python -m pc_checkup`, which is how the elevated relaunch starts the program."""

from pc_checkup.cli import main

raise SystemExit(main())
