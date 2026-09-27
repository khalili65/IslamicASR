#!/usr/bin/env python3
"""Start a command in its own session so it survives the parent shell.

macOS has no setsid(1), and `nohup ... &` still leaves the child in the
caller's process group, so it dies when that group is torn down. Popen with
start_new_session=True calls setsid(2) and fully detaches the child.

Usage: python scripts/detach.py LOGFILE COMMAND [ARGS...]
"""

import subprocess
import sys
from pathlib import Path

if len(sys.argv) < 3:
    sys.exit("usage: detach.py LOGFILE COMMAND [ARGS...]")

log_path = Path(sys.argv[1])
log_path.parent.mkdir(parents=True, exist_ok=True)

with open(log_path, "ab", buffering=0) as log, open("/dev/null", "rb") as devnull:
    child = subprocess.Popen(
        sys.argv[2:],
        stdin=devnull,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

print(child.pid)
