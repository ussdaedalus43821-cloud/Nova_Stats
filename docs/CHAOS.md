# Chaos test: a system command that is gone, or says nothing

`tests/test_chaos.py` (in `tests/run_suite.py`, and on Linux in CI) takes each of the eight commands on
`host.py`'s allowlist away in turn. The command either does not exist (`sh` raises `FileNotFoundError`, as
`subprocess` does for a renamed binary) or prints nothing (`sh` returns `""`). Every other command answers
from `tests/fixtures/`. The real `src/main.nova` then draws one frame.

**Why it does not rename the real commands.** `host.py` runs them by absolute path, and `/usr/bin` and
`/usr/sbin` are read-only on macOS (System Integrity Protection). Replacing `sh` is the same failure as the
command being gone, seen from the NovaLang side.

**Pass condition.** No Python traceback; exit 0; the whole dashboard is drawn (the Clock section is still
there); and the stat that needs the command shows `unavailable: <why>` instead of a number. A failure is
caught by the `try`/`catch` around each reader in `src/pipeline.nova` (`guarded`), so one stat goes and the
rest stay.

| Command | Missing | Blank |
| --- | --- | --- |
| `top` | CPU unavailable | CPU unavailable (`top printed no 'CPU usage:' line`) |
| `sysctl` | CPU and Memory unavailable | Memory unavailable (`hw.memsize is not a number`) |
| `vm_stat` | Memory unavailable | Memory unavailable |
| `df` | Disk unavailable | Disk unavailable (`df printed no volume line`) |
| `netstat` | Network unavailable | Network unavailable (`netstat printed no interface counters`): **fixed** |
| `ioreg` | Battery unavailable | Battery `none`: see below |
| `pmset` | Battery unavailable | Battery drawn, `macOS figure unavailable`: **fixed** |
| `ps` | CPU and Memory unavailable | CPU and Memory drawn without their top-process lists |
| all eight | every stat unavailable, Clock drawn | |

## What the chaos test found (2026-11-14)

- **A blank `netstat` showed `total in 0 B   out 0 B`.** That reads as a real count. `src/modules/net.nova`
  now throws when no interface row is found, so Network shows as unavailable.
- **A blank `pmset` showed `macOS says -1%`.** `-1` is the "not found" value of `parse_pmset`.
  `src/render_term.nova` now shows `macOS figure unavailable`. The battery itself is read from `ioreg`, so the
  rest of the Battery section is still right.

## Left as it is

- **A blank `ioreg` shows `Battery none`.** On a Mac without a battery, `ioreg -rn AppleSmartBattery` prints
  nothing, so a blank answer cannot be told from "no battery". This is the same output a desktop Mac gets.
- **A blank `ps` drops the top-process lists.** The CPU and Memory figures come from `top`, `sysctl` and
  `vm_stat`, so they are still right. The lists are empty, and nothing in them is made up.
- **The label is `unavailable: <why>`, not `[Unavailable]`.** The reason is kept on purpose: it tells you
  which command failed. Changing the wording would also change both golden files.
