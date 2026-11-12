# GAPS.md - where NovaLang struggled building novalang_stats

A stress test, not a safe build: every clunky moment, missing feature and host workaround
found while re-implementing Stats' six modules (CPU, RAM, Disk, Net, Battery, Clock) in
NovaLang v2.2.0 (develop @ 8047a48, which includes the `\033` fix made at the start of this work).

**How to read an entry.** *Tried* is what was attempted and the exact result. *Workaround* says what the
code does instead and **who does the work**: `NovaLang` (written in the program), `host` (Python in
`host.py`) or `none` (cannot be done). *Probe* is a reproducible check: `tests/probes/<file>` is run on both
engines by `python3 tests/probes/run_probes.py`, and fails the day NovaLang is fixed, so the log cannot rot.
`python3 tests/probes/host_probes.py` covers the entries that need Python around them.

**Severity:** BUG (wrong result, no warning) - BLOCKER (needs the host) - FRICTION (worked around in
NovaLang, at a cost) - LIMIT (outside what a scripting language can reach).

## The host boundary, in full

`host.py` is 53 lines. What it supplies, and the gap that made it necessary:

| Host does | Because |
| --- | --- |
| `sh(argv)`, allowlisted, no shell, 5 s limit | NovaLang has no process or system API at all (by design) |
| `ESC` constant | G-004 / G-005 |
| `novalang.SCRIPT_ARGS = [...]` before the program starts | G-015 |
| catches Ctrl-C, prints "Stopping Nova_Stats..." and exits 130 | G-026 |
| `os.chdir` to the project root | file paths are relative to the working directory (a convenience, not a gap) |

Nothing else: no parsing, no arithmetic, no state, no rendering, no file I/O is done in Python.

---

## G-001 Big integers are exact - PASS
- **Tried:** `ioreg` writes a signed 64-bit current as the unsigned number with the same bits (-171 mA is `18446744073709551445`). `kit.signed64` subtracts 2^64 above 2^63.
- **Result:** exact, no precision loss, no special handling. The only place NovaLang is better than the obvious host language for this job (Swift/C need `Int64(bitPattern:)`; JavaScript would have lost the low bits).
- **Probe:** `g001_big_integers.nova`. Also in the suite: "signed64 boundary".

## G-002 `num()` throws on text that is not a number - FRICTION
- **Tried:** `num("abc")` -> `NovaError: num() cannot read a number from "abc"`. Command output is full of text that is not a number (headers, `-`, units).
- **Workaround (NovaLang):** `kit.to_num(text, fallback)` wraps `try/catch`. 23 call sites. There is no `is_number()` or `num(text, default)`.
- **Probe:** `g002_num_throws.nova`

## G-003 `regex()` returns only true or false - FRICTION
- **Tried:** `regex("([0-9]+)%", "65%")` -> `true`. No captures, no match position, no replace, no split-by-pattern.
- **Workaround (NovaLang):** every extraction is `split` plus slicing: `kit.after`, `kit.between`, `kit.word_after`, and line-by-line "state machines" for `top`, `vm_stat`, `ioreg` and `pmset`. `parse_pmset` reads a time by testing each word for `:` instead of matching `\d+:\d\d`.
- **Probe:** `g003_regex_has_no_captures.nova`

## G-004 No way to write an escape character - BLOCKER (host)
- **Tried:** `"\x1b"` -> `unknown escape '\x'`; `"\u001b"` -> `'\u'`; `"\e"` -> `'\e'`; `"\033"` -> `unknown escape '\03'`.
- **History:** `"\033"` used to be a silent trap: `\0` is the null character, so it lexed as NUL followed by the text `33`, and a terminal showed `33[31m` with no error. Fixed at the start of this project (Python lexer, self-hosted lexer, spec `[lex.escapes]`, 4 conformance cases, and the policy dialect). It is now an error, but still not an escape.
- **Workaround (host):** `ESC` is handed over as a global string. The renderer takes it as `style.esc`; `style.color = false` disables it.
- **Consequence:** the self-hosted interpreter has no host to hand it `ESC`, so colour and in-place redraw cannot run there at all (see G-020). The tests render plain text.
- **Probes:** `g004_hex_escape`, `g004_unicode_escape`, `g004_e_escape`, `g004_octal_escape`.

## G-005 No `chr()` / `ord()` - BLOCKER (host)
- **Tried:** `chr(27)` -> `undefined name 'chr'`. This closes the other way to build ESC.
- **Workaround (host):** same `ESC` constant. **Probe:** `g005_no_chr.nova`.

## G-006 No `find`, `index_of`, `startswith` or `endswith` - FRICTION
- **Tried:** `find("abc","b")`, `startswith("abc","a")` -> `undefined name`. `in` answers "is it there" but not "where".
- **Workaround (NovaLang):** `kit.has_prefix` is `text[:len(prefix)] == prefix`; `kit.after` is `split` then `join` of the tail. Used 31 times.
- **Probes:** `g006_no_find.nova`, `g006_no_startswith.nova`

## G-007 No thousands separator, no locale formatting - FRICTION
- **Tried:** `str(1234567)` is `1234567`; no `format`, no locale. Stats shows grouped counts (process counts, packets).
- **Workaround (NovaLang):** `kit.group_digits` (reverse loop inserting commas). Written and tested, but no screen needs it yet, so it is the one helper that is unused.
- **Probe:** covered by the suite ("group_digits"); no separate probe, since the absence is the same as G-008.

## G-008 No number formatting - FRICTION
- **Tried:** `str(5.0)` is `5`; `str(0.05)` is `0.05`; there is no `format()`/`printf` (`undefined name 'format'`), and an f-string placeholder takes no format spec: `f"{5.0:.1f}"` -> `unexpected ':' inside this f-string`. `pad_left(s, n)` pads with spaces only (a third argument is `takes 2 argument(s)`), so there is no zero padding either.
- **Workaround (NovaLang):** `kit.fixed(x, digits)` does fixed-point text with integer arithmetic (`round`, `//`, `%`, string repeat of `"0"`). `kit.two`, `kit.duration`, `kit.human_bytes` sit on top. `kit.group_digits` (thousands separators) is written and tested but the UI does not use it.
- **Probes:** `g008_no_float_format.nova`, `g008_no_printf.nova`, `g024_pad_left_only_spaces.nova`

## G-009 No null, and a missing dictionary key is an error - FRICTION
- **Tried:** `nothing` -> `undefined name 'nothing'` (the value exists but has no name); `{a: 1}.b` -> `this dictionary has no key 'b'`; no `get(d, k, default)`.
- **Workaround (NovaLang):** `"k" in d` before every optional read; "unknown" is `-1` in every duration field (`-1` hours, `-1` minutes) and the only code that turns it into text is `kit.duration` / `kit.minutes_text`. The battery tests spend 9 checks on sentinels (65535, zero current, no estimate, no battery).
- **Probes:** `g009_no_null.nova`, `g009_missing_key_is_an_error.nova`, `g009_no_dict_get.nova`

## G-010 No multi-line strings, no templating, no HTML escaping - FRICTION
- **Tried:** a string literal must end on its own line: `this string is never closed`. There is no triple-quote or heredoc.
- **Workaround (NovaLang):** `render_html.nova` builds the page from ~40 concatenations with `\"` escapes, and writes its own three-`replace_all` HTML escape. 121 lines for a 2.8 KB page.
- **Probe:** `g010_no_multiline_strings.nova`

## G-011 A line that starts with `+` is a new statement, silently - BUG-prone
- **Tried:** wrapping a long concatenation across lines the way every other language allows:
  ```
  def f() {
      return "a"
          + "b"
  }
  print(f())      # prints  a
  ```
  There is no error and no warning: `return "a"` ends the function, the next line is unreachable dead code. Outside a function the same shape is a *runtime* error, `cannot apply unary '+' to a string`.
- **Found while:** writing `render_html.nova`'s page builder; the first draft returned only the `<head>`.
- **Workaround (NovaLang):** long expressions are built with `page = page + ...` one statement at a time. List and dictionary literals may span lines, which hides the problem until an expression is not one.
- **Suggestion:** an unreachable-statement warning (or error) after `return`, and/or a lexical rule that a line starting with a binary operator continues the previous one.
- **Probes:** `g011_plus_at_line_start.nova`, `g011_plus_after_let.nova`

## G-012 No disk I/O rates - LIMIT
Stats reads per-second read/write rates from IOKit. The only source reachable through `sh` is the `Disks:` line of `top`, which rounds to whole gigabytes (`4123G read`), so the Disk module reports cumulative totals and no rate.

## G-013 No Wi-Fi name or signal, public IP, sensors, fans, GPU - LIMIT
CoreWLAN, SMC, IOReport and a network client are all outside `ps`/`top`/`ioreg`/`netstat`. Not attempted; the allowlist deliberately has no `curl`, so nothing leaves the machine.

## G-014 Time zones - LIMIT
`format_time` knows only the machine's zone, and there is no zone database. `clock.nova` derives the local UTC offset by comparing `format_time` with UTC arithmetic on the epoch, and the world clocks are fixed offsets with no daylight-saving rules (New York is wrong for half the year).

## G-015 The embedding API cannot give a program its `args()` - FRICTION (host)
- **Tried:** `Nova().load_file(path)` then `args()` -> `[]` always. The only thing that reaches `args()` is the module global `novalang.SCRIPT_ARGS`, set by the CLI path and by nothing public.
- **Workaround (host):** `host.py` assigns `novalang.SCRIPT_ARGS` directly - reaching into an interpreter global.
- **Probe:** `tests/probes/host_probes.py` (G-015 lines).

## G-016 Natural names are reserved - FRICTION
- **Tried:** `def read(x)` -> `'read' is a built-in function and cannot be used as a function name`; `let time = 5` likewise; `let step = 2` -> `expected a name after 'let'` (`step`, `to`, `with`, `as`, `in` are keywords).
- **Workaround (NovaLang):** every reader's entry point was going to be `read`; all six are `sample`. Variables were renamed on the way (`user_pct`, `system_pct`, `procs`).
- **Probes:** `g016_reserved_names.nova`, `g016_reserved_names_time.nova`, `g031_keyword_names.nova`

## G-017 A program with `import` needs four Python files the interpreter does not mention - FRICTION
- **Tried:** the vendored `novalang.py` + `novalang.nova` + `bootstrap.py` (all the moped sim needed) fails the moment a program has an `import`: a raw Python `FileNotFoundError` for `tools/nova-typecheck.py`.
- **Workaround:** vendor `tools/nova-typecheck.py`, `nova_ast.py`, `nova_scope.py`, `nova_compiler.py` beside it. "A single-file interpreter" is true only for programs without imports.
- **Probe:** `tests/probes/host_probes.py` (G-017 lines).

## G-018 No `exp()`, no power operator - minor
`pow(E, x)` works and is what the charge-model test uses to integrate the decay. Probe: `g018_no_exp.nova`.

## G-019 The two engines word one error differently - conformance
- **Tried:** `"abc".upper()` -> VM `a string has no fields, so '.upper' means nothing here`; self-hosted `string has no fields, ...` (no article). The self-hosted lexer/parser errors are also reported as `Error: LexError@12: ...` where the VM says `NovaError: ...`.
- **Effect:** none on this project (the 160 checks agree), but a program that matches on a caught message would behave differently. The spec marks reports as not compared; the first is a message and is.
- **Probe:** `g030_no_string_methods.nova` (run_probes.py flags the disagreement).

## G-020 The self-hosted interpreter: 31x slower, and it cannot run the dashboard - BLOCKER for that engine
- **Speed:** the same 160-check suite takes 0.63 s on the VM and 19.7 s on `--bootstrap` (31x). One whole tick (parse six readers, model, three renders) is 11 ms on the VM and 649 ms self-hosted (58x).
- **No host binding:** `--bootstrap src/main.nova` -> `undefined name 'ESC'` (and `sh`): there is nothing to expose them through. The live tool runs on the VM only.
- **Workaround (NovaLang):** the readers take their command runner in a `ctx` argument, so the suite hands them a NovaLang `sh` that replays recorded output with `read()`. That is why all six readers, the model, and both renderers run identically on both engines.
- **Parity result:** 160/160 on both. No behavioural difference was found.
- **Probe:** `tests/probes/host_probes.py` (G-020 lines).

## G-021 Assigning to a global from a function silently makes a local - FRICTION
- **Tried:** `let n = 0; def bump() { n = n + 1 }; bump(); bump(); print(n)` prints `0`. Specified behaviour (`[scope.assign]`), but there is no `global` keyword and no error.
- **Workaround (NovaLang):** all state between ticks lives in dictionaries (`state.net`, `state.battery.window`); `kit.cached` keeps its memo in a dictionary for the same reason.
- **Probe:** `g026_assign_to_global_from_function.nova`

## G-022 A caught error is a bare string - FRICTION
- **Tried:** `catch e` gives `index 0 is out of range ...` with no line, no function name, no stack. The dashboard and log can say *which module* failed (because the guard knows) but not where in it.
- **Workaround (NovaLang):** the module name is added by the guard: `ERROR battery: <text>`.
- **Probe:** `g027_errors_carry_no_position.nova`

## G-023 No terminal size, no tty detection, no output control - FRICTION
- **Tried:** `env("COLUMNS")`, `env("LINES")` are both `nothing` (shell variables, not exported); `print` always adds a newline; no `isatty`.
- **Workaround (NovaLang):** fixed 24-cell bars; a `--plain` flag instead of detecting a pipe; the whole frame is built as one string and printed once.
- **Probe:** `g029_no_terminal_size.nova`

## G-024 No test runner, and `assert` stops at the first failure - FRICTION
`assert` is catchable but unnamed, and there is no runner, so `tests/run_tests.nova` carries a 25-line `check`/`near` harness (160 checks).

## G-025 Surprise: unspecified Python exceptions - minor
A host exception shows up in NovaLang as `PythonError: PermissionError: command not allowed: ['/bin/ls']` - catchable, and good enough, but the type name of the *Python* exception is part of the NovaLang message.

## G-026 A NovaLang program cannot handle Ctrl-C, and the embedding API does not either - FRICTION
- **Tried:** pressing Ctrl-C during the live view printed a Python traceback (`KeyboardInterrupt` out of
  `subprocess.run`, inside the host's `sh`). A probe with `try { sleep(5000) } catch e { ... }` and a real SIGINT: the
  `catch` did not run and nothing after the block ran, so NovaLang code cannot intercept an interrupt or clean up.
  The command line (`novalang.py script.nova`) prints `(stopped)` and exits 130, but `Nova().load_file()`, which
  `host.py` uses, lets `KeyboardInterrupt` escape to the embedder.
- **Workaround (host):** `host.py` catches `KeyboardInterrupt` around `load_file`, prints `Stopping Nova_Stats...` to stderr
  and exits 130. Tests: `tests/test_host.py` (`Interrupt`, including a real SIGINT during the first live frame).
- **Suggested fix:** have the embedding API stop a run the way the CLI does (or raise a dedicated, catchable
  error), and document it in the host chapter.
- **Probe:** none yet: a probe needs a signal, so it would live in `tests/probes/host_probes.py`.

---

## What worked (no entry needed)
- Closures and dictionaries are enough for per-tick state, a memoising command cache and the rolling power window.
- `try/catch` isolation per module: a failing `ioreg` marks only the battery unavailable (tested; the log gets one line).
- `json.pretty`/`json.loads` handle the snapshot and the baselines file with no extra code.
- Non-ASCII output (`█`, `░`) needs no special handling.
- Parity: all 160 checks pass identically on both engines.
- Speed on the VM: 11 ms for a whole tick, against 1.3 s for the `top` call it is parsing.
