# Vendored NovaLang

Copied unmodified from the Nova_Lang repository, `develop` at **34a6256** (the merge of pull request 12, M14 slice P1;
NovaLang 2.4.0 in development). Every file below was copied from that commit with `git show`.

| File | Purpose |
| --- | --- |
| `novalang.py` | the interpreter, bytecode VM and CLI |
| `novalang.nova` | the self-hosted interpreter, run by `--bootstrap` |
| `bootstrap.py` | loader for the self-hosted engine |
| `lib/std/` | the standard modules (`std:csv`, `std:date`, `std:decimal`, `std:dict`, `std:files`, `std:format`, `std:hash`, `std:math`, `std:regex`, `std:text`) and their list, `modules.json`. This program uses `std:text` and `std:date` |
| `tools/nova-typecheck.py`, `nova_ast.py`, `nova_scope.py`, `nova_compiler.py` | needed as soon as a program has an `import` (GAPS G-017) |
| `LICENSE-MIT`, `LICENSE-APACHE` | upstream licence (NovaLang is dual MIT OR Apache-2.0; this replaces the single MIT `LICENSE` of the previous copy) |

To update, copy the same files from a newer commit and re-run `python3 tests/run_suite.py`.
