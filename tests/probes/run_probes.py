"""Runs every probe on the VM and on the self-hosted interpreter and checks the observed text
against expected.json. A probe documents a gap in docs/GAPS.md: if NovaLang is ever fixed the
probe fails, which is the signal to update the entry. Run: python3 tests/probes/run_probes.py"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
NOVA = os.path.join(ROOT, "novalang", "novalang.py")
expected = json.load(open(os.path.join(HERE, "expected.json")))

def run(engine, path):
    argv = [sys.executable, NOVA] + (["--bootstrap"] if engine == "self-hosted" else []) + [path]
    done = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=120)
    return (done.stdout + done.stderr).strip(), done.returncode

bad = 0
for name in sorted(expected):
    seen = {}
    for engine in ("vm", "self-hosted"):
        seen[engine] = run(engine, os.path.join("tests", "probes", name))
    ok_vm = expected[name].strip() in seen["vm"][0]
    ok_sh = expected[name].strip() in seen["self-hosted"][0]
    def message(text):
        lines = [l for l in text.splitlines() if "Error:" in l]
        if not lines:
            return text.splitlines()[-1:]
        # the self-hosted lexer and parser prefix "LexError@12: " / "ParseError@4: " to the message
        return re.sub(r"^\w+@\d+: ", "", lines[-1].split("Error:", 1)[1].strip())
    same = message(seen["vm"][0]) == message(seen["self-hosted"][0])
    print("%-46s vm:%-4s self-hosted:%-4s %s" % (name, "ok" if ok_vm else "DIFF", "ok" if ok_sh else "DIFF",
          "" if same else "(ENGINES DISAGREE ON THE MESSAGE)"))
    if not (ok_vm and ok_sh):
        bad += 1
        print("   expected:", repr(expected[name]), "\n   vm:", repr(seen["vm"][0][-200:]), "\n   self-hosted:", repr(seen["self-hosted"][0][-200:]))
print("%d probes, %d disagree with the log" % (len(expected), bad))
sys.exit(1 if bad else 0)
