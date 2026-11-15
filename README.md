# Nova_Stats

> **The first official proof of concept for [NovaLang](https://github.com/ussdaedalus43821-cloud/Nova_Lang), and its first external "Nova Pack" app.**
> It is not a replacement for Stats. It exists to find out where NovaLang struggles when it does a real job.

A terminal and HTML system dashboard (CPU, RAM, Disk, Net, Battery, Clock) that re-implements the logic of
[Stats](https://github.com/exelban/stats) in **NovaLang v2.2.0**, as a stress test: the point is to find where the
language struggles. Every finding is in [`docs/GAPS.md`](docs/GAPS.md).

## Run

```bash
python3 host.py                 # live terminal dashboard (Ctrl-C to stop)
python3 host.py --once          # one tick, then exit
python3 host.py --plain         # no colour or cursor movement (also for pipes)
python3 host.py --frames 5 --interval 2
```

Each tick writes `out/snapshot.json`, `out/dashboard.html`, `out/battery_compare.csv` and `out/runtime.log`.

## How it is built

"Approach A": NovaLang does everything. `host.py` (53 lines) gives the program exactly one thing: `sh(argv)`. NovaLang has no way to run a command, so that one stays in the host.

- `sh` runs one allowlisted, read-only command (`ps`, `df`, `top`, `vm_stat`, `pmset`, `ioreg`, `netstat`, `sysctl`),
  as an argv list with no shell and a 5 s limit. Anything else raises `PermissionError`.
- The escape character for colour and redraw is made in NovaLang since 2.4: `std:text.chr(27)` (G-004, G-005). The colour frame renders identically with no host (`tests/run_tests.nova`). Times go through `std:date` (G-014).

| Path | Role |
| --- | --- |
| `src/modules/*.nova` | one reader per module, each `sample(ctx, state)` |
| `src/battery_model.nova` | power, runtime, charge time, health, wear, benchmark |
| `src/kit.nova` | parsing and formatting helpers NovaLang lacks |
| `src/pipeline.nova` | runs readers, isolates each failure, builds the snapshot |
| `src/render_term.nova`, `render_html.nova` | the two views |
| `src/main.nova` | the loop and the output files |

Readers take their command runner in `ctx`, so tests replay recorded output and the same code runs on both engines.

## Test

```bash
python3 tests/run_suite.py            # NovaLang checks (VM, then --bootstrap) and the Python host tests
python3 tests/probes/run_probes.py    # the gap probes, both engines
python3 tests/probes/host_probes.py   # gaps that need Python around them
```

Fixtures in `tests/fixtures/` are sanitised captures from a real MacBookPro17,1. The discharging and charging
battery fixtures are *derived* (current sign and state substituted); see [`docs/BENCHMARK.md`](docs/BENCHMARK.md).

## Limits

No disk I/O rates, Wi-Fi details, sensors, fans, GPU or public IP (G-012, G-013); no time-zone database (G-014).
The dashboard runs on the VM only; the self-hosted interpreter has no way to receive `sh` (G-020).
