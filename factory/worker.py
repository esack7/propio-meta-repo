"""Hold the inherited factory lease until the foreground command exits."""

import os
import signal
import subprocess
import sys


if __name__ == "__main__":
    try:
        # The supervisor retains the locks if the runner dies. The command
        # and any daemons it launches inherit only their standard streams.
        # The runner normally enforces the deadline. Keep a fallback deadline
        # if it disappeared while a command (for example a signer) was waiting.
        result = subprocess.call(sys.argv[2:], close_fds=True, timeout=float(sys.argv[1]) + 1)
    except subprocess.TimeoutExpired:
        os.killpg(os.getpgrp(), signal.SIGKILL)
    except OSError as exc:
        print(f"Cannot launch {sys.argv[2]}: {exc}", file=sys.stderr)
        result = 127 if isinstance(exc, FileNotFoundError) else 126
    sys.exit(result if result >= 0 else 128 - result)
