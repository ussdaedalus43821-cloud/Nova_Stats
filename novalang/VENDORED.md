# Vendored NovaLang

Copied unmodified from the Nova_Lang repository, branch `develop`, commit **8047a48**
(the commit that makes `\033` an error in all three lexers, including the policy dialect).

| File | Purpose |
| --- | --- |
| `novalang.py` | the interpreter, bytecode VM and CLI |
| `novalang.nova` | the self-hosted interpreter, run by `--bootstrap` |
| `bootstrap.py` | loader for the self-hosted engine |
| `tools/nova-typecheck.py`, `nova_ast.py`, `nova_scope.py`, `nova_compiler.py` | needed as soon as a program has an `import` (GAPS G-017) |
| `LICENSE` | upstream licence |

To update, copy the same files from a newer commit and re-run `python3 tests/run_suite.py`.
