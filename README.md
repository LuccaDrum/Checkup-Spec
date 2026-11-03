# PC Checkup

A Windows command-line tool that checks the health of a PC (blue screens, SSD, RAM) and runs
the standard Windows repairs (SFC, DISM) from a numbered menu. It is written for people who are
not technical: every result is explained in plain words first, and the technical details come
second.

> **Status:** a personal learning project. The read-only checks (options 1 to 3) have been run on
> a real PC. The RAM test cycle (option 4) and the repairs (options 5 and 6) are covered by
> automated tests that simulate Windows, but have not yet been run end to end on a real machine.

## What it does

```
=== PC Checkup ===
1) Run full check
2) Blue screens (last 15 days)
3) SSD health
4) RAM test
5) Repair system files (SFC)
6) Repair Windows image (DISM)
7) Settings (language)
0) Exit
```

| Option | What it does | Changes the PC? |
| --- | --- | --- |
| 1 | Runs 2 and 3 and shows the latest RAM test result | No, read only |
| 2 | Finds blue screens and unexpected shutdowns in the last 15 days and explains the error codes | No, read only |
| 3 | Reads disk health, wear, temperature and errors, and says what the drive does not report | No, read only |
| 4 | Runs the Windows Memory Diagnostic, then shows its result | **Yes, restarts the PC** (see below) |
| 5 | Runs `sfc /scannow` | Yes, repairs system files |
| 6 | Runs `DISM /Online /Cleanup-Image /RestoreHealth` | Yes, repairs the Windows image |
| 7 | Switches the language between English and Portuguese | Saves a setting |

### Safety

- Anything that changes the system (options 4, 5 and 6) first explains what it does, warns about
  the duration and the risks, and asks for confirmation. Any answer other than yes cancels it.
- **Option 4 restarts the PC.** After you confirm, the program schedules the memory test for the
  next boot, sets itself to open again after the restart, and restarts the PC in 15 seconds.
  Save your work first. To cancel the restart, run `shutdown /a` in a terminal. After the test,
  the program opens by itself and shows the result.
- Options 5 and 6 never restart the PC. If DISM says a restart is needed, the program only tells you.
- Results are read from exit codes and event IDs, never from the text of the tools, so the tool
  works the same on any Windows language.

## Requirements

- Windows 10 or 11
- Python 3.11 or newer
- Administrator rights. The program asks for them when it starts (the Windows permission
  prompt) and reopens itself elevated.

## Install and run

```bash
py -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\checkup.exe
```

Run it from a normal terminal. Accept the Windows permission prompt and the menu opens in a new
window. The language setting, a small state file and the log are stored in `%APPDATA%\pc_checkup\`.

The interface language is English by default; use option 7 to switch to Portuguese.

## Logs

Technical details never appear in the menu. They are written to
`%APPDATA%\pc_checkup\checkup.log` (rotated when it grows). If something unexpected goes wrong, the
program says so in plain words and points to this file, which you can send to whoever supports
your PC. Set the environment variable `PC_CHECKUP_DEBUG=1` for more detail.

## How it is organized

```
src/pc_checkup/
├── cli.py              entry point: admin check, then the menu, with final error handling
├── admin.py            is_admin() and relaunching with the Windows permission prompt
├── menu.py             shows options, validates input, dispatches
├── messages.py         every piece of user-facing text, by key and language
├── interpreter.py      raw data -> friendly text + technical details (thresholds in one table)
├── models.py           small immutable data classes
├── ui.py               bold options, separators and colored bands
├── config.py           language setting
├── storage.py          remembers a pending RAM test
├── autostart.py        reopens the program once after the restart (RunOnce)
├── logging_setup.py    logs to a file
├── sources/            read-only: blue screens, SSD, RAM result
└── actions/            change the system: RAM test, SFC, DISM (describe, warn, confirm, run)
```

A few rules the code follows:

- A `Source` only reads and an `Action` changes the system. Every action goes through the same
  four steps, written once in the base class.
- Nothing prints or reads input directly: the menu receives `input_fn` and `print_fn`, and the
  sources and actions receive the functions that call Windows. Tests replace them, so no test
  touches the real PC.
- No `shell=True`, every tool call has a timeout, and output is decoded carefully.
- Every message exists in both languages, and a test checks it.

## Development

```bash
.venv\Scripts\python.exe -m pytest --cov=pc_checkup --cov-report=term-missing
.venv\Scripts\ruff.exe check .
.venv\Scripts\mypy.exe src tests
```

The tests use fixtures saved from real Windows output (in `tests/fixtures/`) and fake system
calls, so they pass on any machine.

## Known limits

- Windows only. There is no installer yet; it needs Python.
- SFC: only exit code 0 is explained. Any other code is reported as "could not finish", with
  the code and the log path, until real runs show what else it returns.
- Some drives, especially behind a RAID controller, report placeholder values (for example
  0 degrees). The program ignores those and says that the detailed data is not available.
- The RAM test result parser has only been checked against a hand-made sample, because the
  Windows Memory Diagnostic has not yet been run on the development PC.

## License

Released under the [MIT License](LICENSE).

## Out of scope for now

Performance monitoring, history of past runs, comparing runs, notifications, a graphical
interface, packaging as an `.exe`, and Linux support.
