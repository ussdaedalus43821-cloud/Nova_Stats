"""Chaos test: each system command the dashboard uses goes missing, or prints nothing, one at a time.

    python3 -m unittest tests.test_chaos            (from the project root; run_suite.py runs it too)

The commands cannot really be renamed: host.py runs them by absolute path, and /usr/bin and /usr/sbin
are read-only on macOS (System Integrity Protection). So the child process below loads the real host.py
and replaces its `sh` with one that answers from tests/fixtures/, except for the one command under
test, which raises FileNotFoundError (the command does not exist) or returns "" (it printed nothing).
The real src/main.nova then runs one frame: the terminal view and out/dashboard.html.

Pass condition: no Python traceback, exit 0, the Clock section still drawn, and the stat that needs the
command shows "unavailable" (or, for the few cases in docs/CHAOS.md, a figure that is honestly empty)
instead of a made-up number. See docs/CHAOS.md for what each case shows and why.
"""
import os, subprocess, sys, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "tests", "fixtures")
SYSCTL = {"hw.memsize": "sysctl_memsize.txt", "hw.ncpu": "sysctl_ncpu.txt",
          "machdep.cpu.brand_string": "sysctl_brand.txt", "vm.swapusage": "sysctl_swap.txt",
          "kern.memorystatus_vm_pressure_level": "sysctl_pressure.txt"}
FILES = {"top": "top.txt", "vm_stat": "vm_stat.txt", "df": "df_data.txt", "netstat": "netstat_a.txt",
         "ioreg": "ioreg_discharging_65.txt", "pmset": "pmset_discharging.txt"}

# command -> (mode -> what its section must show). "unavailable" means the section's own line
# "  unavailable: <why>"; any other text must appear in that section instead.
CASES = {
    "/usr/bin/top":      {"section": "CPU",     "missing": "unavailable", "blank": "unavailable"},
    "/usr/sbin/sysctl":  {"section": "Memory",  "missing": "unavailable", "blank": "unavailable"},
    "/usr/bin/vm_stat":  {"section": "Memory",  "missing": "unavailable", "blank": "unavailable"},
    "/bin/df":           {"section": "Disk",    "missing": "unavailable", "blank": "unavailable"},
    "/usr/sbin/netstat": {"section": "Network", "missing": "unavailable", "blank": "unavailable"},
    "/usr/sbin/ioreg":   {"section": "Battery", "missing": "unavailable", "blank": "  none"},
    "/usr/bin/pmset":    {"section": "Battery", "missing": "unavailable", "blank": "macOS figure unavailable"},
    "/bin/ps":           {"section": "CPU",     "missing": "unavailable", "blank": "total "},
}
SECTIONS = ("CPU", "Memory", "Disk", "Network", "Battery", "Clock")


def fixture_sh(argv):
    name = os.path.basename(argv[0])
    if name == "ps":
        file = "ps.txt" if "pcpu" in argv[2] else "ps_mem.txt"
    elif name == "sysctl":
        file = SYSCTL[argv[2]]
    else:
        file = FILES[name]
    with open(os.path.join(FIX, file), encoding="utf-8") as f:
        return f.read()


def child(target, mode):
    sys.path.insert(0, ROOT)
    import host

    def sh(argv):
        argv = list(argv)
        if argv and argv[0] == target:
            if mode == "missing":
                raise FileNotFoundError(2, "No such file or directory", target)
            return ""
        return fixture_sh(argv)
    host.sh = sh
    return host.main(["--once", "--plain"])


def sections(text):
    """{title: [lines]} of the plain terminal view."""
    found, current = {}, None
    for line in text.splitlines():
        word = line.split(" ")[0]
        if word in SECTIONS:
            current = word
            found[current] = [line]
        elif current and line:
            found[current].append(line)
        elif not line:
            current = None
    return found


class Chaos(unittest.TestCase):
    def run_case(self, target, mode):
        done = subprocess.run([sys.executable, os.path.abspath(__file__), "--child", target, mode],
                              cwd=ROOT, capture_output=True, text=True, timeout=120)
        return done, sections(done.stdout)

    def test_every_command_missing_or_blank(self):
        for target, case in CASES.items():
            for mode in ("missing", "blank"):
                with self.subTest(command=target, mode=mode):
                    done, shown = self.run_case(target, mode)
                    self.assertNotIn("Traceback", done.stdout + done.stderr)
                    self.assertEqual(done.returncode, 0, done.stderr[-2000:])
                    self.assertIn("Clock", shown, "the whole dashboard must still be drawn")
                    body = "\n".join(shown.get(case["section"], []))
                    if case[mode] == "unavailable":
                        self.assertIn("  unavailable: ", body)
                    else:
                        self.assertIn(case[mode], body)
                        self.assertNotIn("unavailable: ", body)
                    self.assertNotIn("-1%", done.stdout, "a missing figure must not be printed as a number")

    def test_the_other_sections_are_untouched(self):
        # netstat feeds only the Network section: everything else is drawn as usual
        done, shown = self.run_case("/usr/sbin/netstat", "missing")
        for title in ("CPU", "Memory", "Disk", "Battery"):
            self.assertNotIn("unavailable", "\n".join(shown[title]), title)

    def test_every_command_at_once(self):
        done = subprocess.run([sys.executable, os.path.abspath(__file__), "--child", "*", "missing"],
                              cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertNotIn("Traceback", done.stdout + done.stderr)
        self.assertEqual(done.returncode, 0)
        shown = sections(done.stdout)
        for title in ("CPU", "Memory", "Disk", "Network", "Battery"):
            self.assertIn("  unavailable: ", "\n".join(shown[title]), title)
        self.assertIn("Clock", shown)


if __name__ == "__main__":
    if sys.argv[1:2] == ["--child"]:
        target, mode = sys.argv[2], sys.argv[3]
        if target == "*":
            def gone(argv):
                raise FileNotFoundError(2, "No such file or directory", argv[0])
            sys.path.insert(0, ROOT)
            import host
            host.sh = gone
            sys.exit(host.main(["--once", "--plain"]))
        sys.exit(child(target, mode))
    unittest.main()
