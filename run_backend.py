#!/usr/bin/env python3
"""
Run gunicorn with stderr filtered to drop NNPACK C++ warnings ("Unsupported hardware").
PyTorch pre-built wheels often ignore USE_NNPACK=0; this wrapper filters at process level.
"""
import os
import sys
import subprocess
import signal
import threading

# Set before any subprocess so gunicorn inherits it
os.environ["USE_NNPACK"] = "0"

def _filtered_stderr_reader(pipe, dest_fd):
    """Read from pipe, drop NNPACK lines, write rest to dest_fd."""
    try:
        for line in iter(pipe.readline, b""):
            if not line:
                break
            try:
                text = line.decode("utf-8", errors="replace")
            except Exception:
                text = str(line)
            if "NNPACK" in text and ("Unsupported hardware" in text or "Could not initialize NNPACK" in text):
                continue
            os.write(dest_fd, line)
    except (OSError, ValueError):
        pass
    finally:
        pipe.close()

def main():
    dest_fd = sys.stderr.fileno()
    proc = subprocess.Popen(
        ["gunicorn", "--config", "gunicorn_config.py", "api:app"],
        stdout=sys.stdout,
        stderr=subprocess.PIPE,
        env=os.environ,
        pass_fds=(),
    )
    t = threading.Thread(target=_filtered_stderr_reader, args=(proc.stderr, dest_fd), daemon=True)
    t.start()

    def sig_handler(signum, frame):
        proc.send_signal(signum)

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(sig, sig_handler)
        except (ValueError, OSError):
            pass

    sys.exit(proc.wait())

if __name__ == "__main__":
    main()
