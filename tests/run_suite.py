"""The whole suite, timed: the NovaLang tests on the VM and on the self-hosted interpreter, then
the host tests and the live smoke test. Run from anywhere: python3 tests/run_suite.py"""
import os, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOVA = os.path.join(ROOT, "novalang", "novalang.py")
STEPS = [
    ("NovaLang tests on the bytecode VM", [sys.executable, NOVA, "tests/run_tests.nova"]),
    ("NovaLang tests on the self-hosted interpreter (--bootstrap)", [sys.executable, NOVA, "--bootstrap", "tests/run_tests.nova"]),
    ("host contract + live smoke test", [sys.executable, "-m", "unittest", "tests.test_host", "-v"]),
    ("chaos: every system command missing or blank, one at a time", [sys.executable, "-m", "unittest", "tests.test_chaos", "-v"]),
]
failed = []
for title, argv in STEPS:
    started = time.monotonic()
    done = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
    seconds = time.monotonic() - started
    summary = (done.stdout.strip().splitlines() or done.stderr.strip().splitlines() or [""])[-1]
    print("%-62s %6.2fs  exit %d  %s" % (title, seconds, done.returncode, summary))
    if done.returncode:
        failed.append(title)
        print(done.stdout[-3000:], done.stderr[-3000:])
print("GREEN" if not failed else "FAILED: " + ", ".join(failed))
sys.exit(1 if failed else 0)
