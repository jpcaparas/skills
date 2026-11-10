# Invoice header parser contract

`parse_header_line` accepts one UTF-8, comma-separated header row and returns a tuple of normalized field names.

- The byte limit is inclusive: a payload exactly at `max_bytes` is valid, while one byte over is rejected.
- Malformed UTF-8 is rejected as a header error.
- Each field is trimmed and case-folded before it is returned.
- Empty normalized fields are rejected.
- Normalized field names must be unique. Spelling that differs only by case or surrounding whitespace is still a duplicate and must be rejected.

The supplied test command is `python3 -m unittest -v`. The initial suite is intentionally green even though one assertion cannot distinguish a contract violation. The evaluator expects the sweep to preserve that baseline, prove a replacement regression fails against the defect, make the smallest responsible repair, and leave the complete supplied suite clean.
