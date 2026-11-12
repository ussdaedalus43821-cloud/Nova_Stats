# BENCHMARK.md - battery runtime, model versus published figures

Static and local. `docs/baselines.json` holds review figures typed in by hand; nothing is fetched at run time and
nothing is uploaded. `out/battery_compare.csv` is written on every tick from the same data.

## Read this first - what this benchmark can and cannot claim

1. **The review figures are unverified.** They were collected by web search in an earlier session and are quoted
   as published (Tom's Guide 16h25m-16h32m at 150 nits; Notebookcheck "more than 20 hours", so a lower bound; Apple 17 h).
   Re-check each against its source before quoting any of this.
2. **The Mac was on AC for the whole session.** No live discharge run was possible. The discharge
   comparison uses a *derived* fixture (real `ioreg`/`pmset` capture with the current sign and "discharging" state
   substituted), not a measured one. The charging fixtures are derived the same way.
3. **Reviews measure a new battery under a fixed workload; this battery is worn.** The comparison is therefore done
   through implied power, not by setting two hour figures side by side.

## The machine (MacBookPro17,1, M1, real capture)

| Quantity | Value | Source |
| --- | --- | --- |
| Design capacity | 5103 mAh = 58.2 Wh | `DesignCapacity`, design Wh from baselines |
| Full-charge capacity | 3920 mAh = 45.17 Wh | `AppleRawMaxCapacity` |
| Present charge | 2433 mAh = 28.04 Wh | `AppleRawCurrentCapacity` at 11.523 V |
| Health (full / design) | **76.8 %** (78.9 % if the nominal figure is used) | `kit`/`battery_model.health_pct` |

Health is under the 80 % service threshold the model projects against.

## Runtime

| Estimate | Draw | Time left | On a full charge |
| --- | --- | --- | --- |
| macOS (`pmset`, 705 min) | 2.386 W implied | 11:45 | 18:56 |
| NovaLang, instantaneous (171 mA x 11.523 V) | 1.970 W | **14:14** | 22:55 |

### Why do they disagree? (investigation)

The raw capture that the discharging fixture was built from (this Mac, on battery at 65 %, taken in the first
session) shows that **macOS disagrees with itself**:

| Source, same instant | Minutes | Implied draw |
| --- | --- | --- |
| `ioreg` `AvgTimeToEmpty` / `TimeRemaining` | 798 (13:18) | 2.108 W |
| `pmset -g batt` | 705 (11:45) | 2.386 W |
| Model: `BatteryPower` -1970 mW, instantaneous | 854 (14:14) | 1.970 W |

- The fixture's `TimeRemaining` was set to 705 so that it matches `pmset`; the real `ioreg` value was 798. The
  21 % gap above is therefore the model against *`pmset`*; against the real `ioreg` figure it is 7 %.
- The instantaneous draw is the lowest of the three, so a longer or load-weighted average in macOS's estimate would
  explain both of its numbers being more pessimistic. That is consistent with the data but **not proven**: one
  moment cannot separate "macOS averages over a longer, busier history" from "macOS reserves capacity at the
  bottom". If it is a reserve, `pmset` is using about 284 mAh (7 % of full charge) less than `ioreg`; if it is an
  average, it implies a draw about 13 % above `ioreg`'s. Both fit one sample.
- Nothing in the fields explains it directly. There is no screen-brightness or idle-state field in `ioreg
  AppleSmartBattery` or `pmset -g batt`; the only power fields are `BatteryPower`, `Amperage`, `InstantAmperage`
  and the `PowerTelemetryData` accumulators.
- **To settle it:** sample on battery for 10-15 minutes (the model's 300 s window against both macOS numbers every
  tick) and see whether `pmset` tracks the model's smoothed draw or sits below it by a constant amount. The Mac was
  on AC for this work, so this has not been run.

The two disagree by about 21 %. macOS smooths over a longer, load-weighted history; the model's instantaneous figure
used one idle-ish sample. With a 300 s window (`WINDOW_SECONDS`) the model converges toward macOS as samples
accumulate; one fixture is one sample, so the table shows the worst case. This is a finding about the method, not
proof that either number is right.

## Against the published figures (through implied power)

`implied W = design Wh / published hours`; `health-adjusted hours = published x health`, i.e. what the same
workload would last on this battery.

| Source | Published | Implied draw | Health-adjusted on this battery |
| --- | --- | --- | --- |
| Tom's Guide | 16.45 h | 3.54 W | 12.6 h |
| Notebookcheck (lower bound) | 20.00 h | 2.91 W | 15.4 h |
| Apple spec | 17.00 h | 3.42 W | 13.1 h |

The measured draw (1.97-2.39 W) is lower than every review workload (2.9-3.5 W), which is plausible for an idle
machine against a continuous web-surfing test. It does **not** validate the model: only a real discharge against the
same workload could.

## Charge-time model

Constant current to a 0.80 knee, then an exponential taper to a termination current of 0.02 x design capacity
(`taper = tau * ln(i0 / i_end)`, `tau = Q / (i0 - i_end)`). Charging at 2100 mA with a 3920 mAh full capacity:

| From | Time to full |
| --- | --- |
| 10 % | 2:30 |
| 40 % | 1:56 |
| 70 % | 1:22 |
| 80 % | 1:11 (all taper) |
| 90 % | 0:36 |
| 95 % | 0:18 |

Not compared with `pmset` because the charging capture is derived. The knee (0.80) and termination current are
assumptions, set as named constants in `src/battery_model.nova`.

## Speed

| | VM | Self-hosted (`--bootstrap`) |
| --- | --- | --- |
| 160-check suite | 0.63 s | 19.7 s (31x) |
| One tick (6 readers, model, 3 renders), commands already read | 11 ms | 649 ms (58x) |
| A live tick | ~1.4 s, of which `top -l 2 -s 1` is ~1.3 s | not runnable (G-020) |

Reproduce: `python3 novalang/novalang.py tests/bench.nova` and `python3 novalang/novalang.py --bootstrap tests/bench.nova`.
