#!/usr/bin/env python3

import json
import sys
from pathlib import Path


def main() -> int:
    source = Path(sys.argv[1])
    events = [json.loads(line) for line in source.read_text().splitlines() if line]
    errors = [event for event in events if event.get("level") == "error"]
    print(json.dumps({"events": len(events), "errors": len(errors)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
