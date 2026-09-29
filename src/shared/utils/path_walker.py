"""path_walker.py — Walk a path backwards to find the last existing segment.

Usage:
    python path_walker.py <path>

Output (stdout):
    If path exists fully:
        OK: <path>
    If path does not exist:
        LAST_EXISTS: <last existing segment, or "(none)" if root also missing>
        MISSING: <remaining parts that do not exist>

Exit codes:
    0 — path exists and is accessible
    1 — path does not fully exist (LAST_EXISTS + MISSING printed)
    2 — wrong usage
"""

import os
import sys


def walk_backwards(path):
    """Return (last_existing, missing_parts) walking path from end to start."""
    path = os.path.normpath(path)
    missing_parts = []
    current = path

    while True:
        if os.path.exists(current):
            return current, missing_parts
        parent = os.path.dirname(current)
        if parent == current:
            return None, [path]
        missing_parts.insert(0, os.path.basename(current))
        current = parent


def main():
    if len(sys.argv) < 2:
        print("Usage: python path_walker.py <path>", file=sys.stderr)
        sys.exit(2)

    path = sys.argv[1]

    if os.path.exists(path):
        print(f"OK: {path}")
        sys.exit(0)

    last_existing, missing_parts = walk_backwards(path)

    if last_existing:
        print(f"LAST_EXISTS: {last_existing}")
        print(f"MISSING: {os.path.join(*missing_parts) if missing_parts else ''}")
    else:
        print("LAST_EXISTS: (none)")
        print(f"MISSING: {path}")

    sys.exit(1)


if __name__ == "__main__":
    main()
