"""Gap probes that need Python around them. Each prints what it saw; docs/GAPS.md cites the result.
Run: python3 tests/probes/host_probes.py"""
import os, shutil, subprocess, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NOVA = os.path.join(ROOT, "novalang", "novalang.py")
sys.path.insert(0, os.path.join(ROOT, "novalang"))
failures = 0

def expect(label, condition, detail=""):
    global failures
    print("%-4s %s %s" % ("ok" if condition else "DIFF", label, detail))
    failures += 0 if condition else 1

# G-015: the embedding API has no way to hand args() to a program.
import novalang
from novalang import Nova
with tempfile.TemporaryDirectory() as tmp:
    path = os.path.join(tmp, "a.nova")
    open(path, "w").write("len(args())\n")
    expect("G-015 args() under Nova() is empty", Nova().load_file(path) == 0)
    novalang.SCRIPT_ARGS = ["--once"]
    expect("G-015 only the module global SCRIPT_ARGS reaches args()", Nova().load_file(path) == 1)
    novalang.SCRIPT_ARGS = []

# G-017: a program with an import will not start unless tools/ is vendored beside novalang.py.
with tempfile.TemporaryDirectory() as tmp:
    for f in ("novalang.py", "novalang.nova", "bootstrap.py"):
        shutil.copy(os.path.join(ROOT, "novalang", f), tmp)
    open(os.path.join(tmp, "util.nova"), "w").write("export def one() { return 1 }\n")
    open(os.path.join(tmp, "main.nova"), "w").write('import "util.nova" as util\nprint(util.one())\n')
    done = subprocess.run([sys.executable, os.path.join(tmp, "novalang.py"), os.path.join(tmp, "main.nova")],
                          capture_output=True, text=True, cwd=tmp)
    expect("G-017 import without tools/ fails with a Python traceback", "nova-typecheck.py" in done.stderr and done.returncode != 0,
           "(last line: %s)" % (done.stderr.strip().splitlines() or [""])[-1][:90])
    shutil.copytree(os.path.join(ROOT, "novalang", "tools"), os.path.join(tmp, "tools"))
    done = subprocess.run([sys.executable, os.path.join(tmp, "novalang.py"), os.path.join(tmp, "main.nova")],
                          capture_output=True, text=True, cwd=tmp)
    expect("G-017 and runs once the four tools/ files are beside it", done.stdout.strip() == "1")

# G-020: the self-hosted interpreter has no host functions to hand it, so the live tool cannot run on it.
done = subprocess.run([sys.executable, NOVA, "--bootstrap", "src/main.nova", "--once", "--plain"], cwd=ROOT,
                      capture_output=True, text=True, timeout=120)
text = done.stdout + done.stderr
expect("G-020 main.nova cannot run on --bootstrap", done.returncode != 0 and "undefined name 'ESC'" in text,
       "(%s)" % [l for l in text.splitlines() if "undefined name" in l][:1])

# G-020: speed of the same 160-check suite on the two engines.
times = {}
for name, extra in (("vm", []), ("self-hosted", ["--bootstrap"])):
    t = time.monotonic()
    subprocess.run([sys.executable, NOVA] + extra + ["tests/run_tests.nova"], cwd=ROOT, capture_output=True, text=True)
    times[name] = time.monotonic() - t
print("     G-020 suite time: vm %.2fs, self-hosted %.2fs (%.0fx)" % (times["vm"], times["self-hosted"], times["self-hosted"] / times["vm"]))
sys.exit(1 if failures else 0)
