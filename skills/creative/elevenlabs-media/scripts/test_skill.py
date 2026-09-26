#!/usr/bin/env python3
"""Run package checks and offline transport regressions, never live generations."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from validate import validate


def main() -> int:
    root = (
        Path(sys.argv[1]).resolve()
        if len(sys.argv) == 2
        else Path(__file__).resolve().parents[1]
    )
    errors = validate(root)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    suite = unittest.defaultTestLoader.discover(
        str(root / "scripts"), pattern="test_helper.py"
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print("Behavioral/trigger scenarios are structurally checked, not model-evaluated.")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
