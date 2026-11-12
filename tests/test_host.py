"""Tests for host.py (the only Python) and a live smoke test on this machine.
Run: python3 -m unittest tests.test_host   (from the project root)"""
import contextlib, io, json, os, signal, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import host
from novalang import Nova


class HostContract(unittest.TestCase):
    def test_esc_is_the_escape_character(self):
        self.assertEqual(host.ESC, "\x1b")

    def test_an_allowed_command_runs(self):
        self.assertEqual(int(host.sh(["/usr/sbin/sysctl", "-n", "hw.ncpu"])), os.cpu_count())

    def test_a_command_off_the_list_is_refused_loudly(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), self.assertRaises(PermissionError):
            host.sh(["/bin/ls", "/"])
        self.assertIn("refused", err.getvalue())

    def test_a_shell_string_is_refused(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(PermissionError):
            host.sh("ps -A")          # a string is not an argv list: its first element is "p"

    def test_an_empty_argv_is_refused(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(PermissionError):
            host.sh([])

    def test_a_slow_command_times_out_loudly(self):
        original = (host.TIMEOUT_SECONDS, set(host.ALLOWED))
        host.TIMEOUT_SECONDS = 0.2
        host.ALLOWED.add("/bin/sleep")
        try:
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(subprocess.TimeoutExpired):
                host.sh(["/bin/sleep", "3"])
        finally:
            host.TIMEOUT_SECONDS = original[0]
            host.ALLOWED.clear(); host.ALLOWED.update(original[1])

    def test_the_allowlist_holds_only_read_only_tools(self):
        for command in host.ALLOWED:
            self.assertTrue(os.path.basename(command) in
                            {"ps", "df", "top", "vm_stat", "pmset", "ioreg", "netstat", "sysctl"}, command)

    def test_novalang_sees_a_refusal_as_a_catchable_error(self):
        nova = Nova()
        nova.expose_global("sh", host.sh)
        with tempfile.NamedTemporaryFile("w", suffix=".nova", delete=False) as f:
            f.write('let r = "no error"\ntry { sh(["/bin/ls"]) } catch e { r = e }\nr\n')
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                result = nova.load_file(f.name)
        finally:
            os.unlink(f.name)
        self.assertIn("not allowed", result)


class LiveSmoke(unittest.TestCase):
    def test_two_real_ticks_on_this_machine(self):
        done = subprocess.run([sys.executable, os.path.join(ROOT, "host.py"), "--frames", "2", "--interval", "1", "--plain"],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        for heading in ("CPU", "Memory", "Disk", "Network", "Battery", "Clock"):
            self.assertIn(heading, done.stdout)
        with open(os.path.join(ROOT, "out", "snapshot.json")) as f:
            snap = json.load(f)
        self.assertEqual(sorted(snap["modules"]), ["battery", "clock", "cpu", "disk", "net", "ram"])
        for name, module in snap["modules"].items():
            self.assertTrue(module["ok"], "%s: %s" % (name, module.get("error")))
        self.assertTrue(snap["modules"]["net"]["have_rate"], "the second tick should have a rate")
        self.assertGreater(snap["modules"]["ram"]["total"], 0)
        with open(os.path.join(ROOT, "out", "dashboard.html")) as f:
            self.assertIn("<!doctype html>", f.read())

    def test_color_mode_writes_escape_codes_through_the_host_constant(self):
        done = subprocess.run([sys.executable, os.path.join(ROOT, "host.py"), "--once"],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("\x1b[H", done.stdout)
        self.assertIn("\x1b[K", done.stdout)
        self.assertTrue(done.stdout.rstrip().endswith("\x1b[J"))


class Interrupt(unittest.TestCase):
    """Ctrl-C is how the live view ends: a message and exit code 130, never a traceback."""

    def test_an_interrupt_inside_the_program_ends_quietly(self):
        err = io.StringIO()
        original = Nova.load_file
        Nova.load_file = lambda self, path: (_ for _ in ()).throw(KeyboardInterrupt())
        try:
            with contextlib.redirect_stderr(err):
                code = host.main(["--once"])
        finally:
            Nova.load_file = original
        self.assertEqual(code, 130)
        self.assertIn("Stopping Nova_Stats", err.getvalue())
        self.assertNotIn("Traceback", err.getvalue())

    def test_a_real_sigint_during_the_live_view(self):
        proc = subprocess.Popen([sys.executable, "-u", os.path.join(ROOT, "host.py"), "--interval", "1"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            proc.stdout.read(1)                      # the first frame has started
            proc.send_signal(signal.SIGINT)
            _, err = proc.communicate(timeout=20)
        finally:
            if proc.poll() is None:
                proc.kill()
        self.assertEqual(proc.returncode, 130, err)
        self.assertIn("Stopping Nova_Stats", err)
        self.assertNotIn("Traceback", err)


if __name__ == "__main__":
    unittest.main()
