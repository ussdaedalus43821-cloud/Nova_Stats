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
- **To settle it:** sample on battery and see whether `pmset` tracks the draw or sits away from it by a constant
  amount. A first, short run on battery is recorded below ("Measured on battery"); a 10-15 minute run is still open.

The two disagree by about 21 %. macOS smooths over a longer, load-weighted history; the model's instantaneous figure
used one idle-ish sample. With a 300 s window (`WINDOW_SECONDS`) the model converges toward macOS as samples
accumulate; one fixture is one sample, so the table shows the worst case. This is a finding about the method, not
proof that either number is right.

### Measured on battery (2026-11-12, live, not a fixture)

A later session ran on battery, so the question could be tested instead of argued. Two things were seen.

**1. The two macOS numbers are different quantities, and `pmset` is the pessimistic one.** In a live run the dashboard
showed a smoothed runtime of 5:57 against macOS's 3:32 (a reading from the dashboard, not reproduced below). A
read-only sampler (`ioreg` and `pmset -g batt` every 15 s for two minutes, about 2830 mAh left, ~11.7 V) shows why:

| t | Current | Draw | `ioreg` AvgTimeToEmpty | remaining / current | `pmset` | draw `pmset` implies |
| --- | --- | --- | --- | --- | --- | --- |
| 0-30 s | -901 mA | 10.35 W | 275 min | 188 min | 242 min | 8.05 W |
| 45-90 s | -386 mA | 4.51 W | 424 min | 441 min | 252 min | 7.89 W |
| 105-120 s | -485 mA | 5.64 W | 333 min | 349 min | 262 min | 7.53 W |

- `ioreg` `AvgTimeToEmpty` follows the current: it moved 275 -> 424 -> 333 min as the draw fell and rose, and it
  sits close to remaining capacity / present current (and so to the model's instantaneous figure). It is a short
  average, and it lags the current a little (275 against 188 min after the jump up to 901 mA).
- `pmset` barely reacted: 242 -> 252 -> 262 min, a steady climb of about 10 min per gauge update while the current
  swung between 386 and 901 mA. The draw it implies (8.05 -> 7.53 W) stayed above the draw actually measured in the
  same two minutes (about 6.7 W on average) and fell slowly towards it.
- The gauge only updates about every 45 s: three samples in a row were identical each time.

**2. What that says about the cause.** A reserve of capacity at the bottom (the other explanation from above) would
make `pmset`'s minutes scale with the current, just shifted down, and they did not: a 2.3x change in current moved
`pmset` by about 4%. A long, load-weighted average of power does fit. The machine had just run a sustained
CPU+GPU load and a full test suite, and `pmset` was still carrying that history, whereas the model's 300 s window
(`WINDOW_SECONDS`) and `ioreg`'s average had already moved on. So in this run `pmset` is not wrong, it is answering "how
long at the load of the last while", and the model answers "how long at about this draw".

**What this does not show.** The sampling lasted two minutes, so the length of `pmset`'s window is unknown (it is
longer than the model's 300 s, but this cannot say by how much). Which workload history `pmset` holds is inferred from
what had been running, not read from anywhere. There is no field in `ioreg` or `pmset` that exposes either window.
One session on one battery (worn: 76-77 % health, 630 cycles). Reproduce with the two commands above, sampled
while changing the load.

**Consequence for the dashboard:** showing the macOS figure next to the model's, labelled by what each one assumes,
is more honest than treating the gap as an error in either; the dashboard already prints both.

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
