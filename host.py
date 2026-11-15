"""The only Python in novalang_stats: it gives the NovaLang program the one thing the language
has no way to do for itself, then gets out of the way.

  sh(argv)  run one allowlisted, read-only command (a list, never a shell string); 5 s limit

(Until NovaLang 2.4 it also handed over ESC, the terminal escape character; the program now makes
it with std:text.chr(27): docs/GAPS.md G-004, G-005.)

Every other thing this file does is recorded in docs/GAPS.md as a host compensation.
Usage: python3 host.py [--once] [--frames N] [--interval SECONDS] [--plain]
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "novalang"))
import novalang
from novalang import Nova

ALLOWED = {"/bin/ps", "/bin/df", "/usr/bin/top", "/usr/bin/vm_stat", "/usr/bin/pmset",
           "/usr/sbin/ioreg", "/usr/sbin/netstat", "/usr/sbin/sysctl"}
TIMEOUT_SECONDS = 5


def sh(argv):
    """A refusal or a timeout is a loud error, never an empty answer."""
    argv = list(argv)
    if not argv or argv[0] not in ALLOWED:
        print("host: refused %r (not on the allowlist)" % (argv[:1],), file=sys.stderr)
        raise PermissionError("command not allowed: %r" % (argv[:1],))
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=TIMEOUT_SECONDS).stdout
    except subprocess.TimeoutExpired:
        print("host: %r ran longer than %ds" % (argv, TIMEOUT_SECONDS), file=sys.stderr)
        raise


def main(arguments):
    os.chdir(HERE)
    novalang.SCRIPT_ARGS = list(arguments)   # the embedding API has no way to pass args() (G-015)
    nova = Nova()
    nova.expose_global("sh", sh)
    try:
        nova.load_file(os.path.join(HERE, "src", "main.nova"))
    except KeyboardInterrupt:
        # Ctrl-C is how the live view is meant to end: say so and use the shell's code for SIGINT.
        # The interrupt lands inside whichever call is running (usually the 1 s `top` sample).
        print("\nStopping Nova_Stats...", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
