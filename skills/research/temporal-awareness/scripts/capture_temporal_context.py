#!/usr/bin/env python3
"""Capture the current local and UTC temporal context for a session."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import socket
import sys
import time
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None


def format_offset(offset: dt.timedelta | None) -> str:
    if offset is None:
        return "+00:00"
    total_seconds = int(offset.total_seconds())
    sign = "+" if total_seconds >= 0 else "-"
    total_seconds = abs(total_seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    return f"{sign}{hours:02d}:{minutes:02d}"


def maybe_extract_zone_from_localtime() -> tuple[str | None, str | None]:
    localtime = Path("/etc/localtime")
    if not localtime.exists() or not localtime.is_symlink():
        return None, None

    try:
        target = os.readlink(localtime)
    except OSError:
        return None, None

    marker = "zoneinfo/"
    if marker in target:
        return target, target.split(marker, 1)[1]
    return target, None


def detect_timezone(now: dt.datetime) -> dict:
    env_tz = os.environ.get("TZ")
    localtime_target, symlink_zone = maybe_extract_zone_from_localtime()
    tzinfo = now.tzinfo
    zone_key = getattr(tzinfo, "key", None)
    abbreviation = now.tzname() or "local"
    candidates = []

    for candidate in [env_tz, symlink_zone, zone_key, abbreviation]:
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    primary = candidates[0] if candidates else "local"
    confidence = "high" if "/" in primary or primary == "UTC" else "medium"

    return {
        "primary": primary,
        "abbreviation": abbreviation,
        "utc_offset": format_offset(now.utcoffset()),
        "environment_tz": env_tz,
        "zoneinfo_key": zone_key,
        "localtime_symlink_target": localtime_target,
        "localtime_zone": symlink_zone,
        "confidence": confidence,
        "dst_in_effect": bool(now.dst()),
        "candidates": candidates,
    }


def build_time_record(moment: dt.datetime) -> dict:
    iso_year, iso_week, iso_weekday = moment.isocalendar()
    return {
        "iso": moment.isoformat(),
        "date": moment.date().isoformat(),
        "time": moment.strftime("%H:%M:%S"),
        "weekday": moment.strftime("%A"),
        "year": moment.year,
        "month": moment.month,
        "day": moment.day,
        "quarter": f"Q{((moment.month - 1) // 3) + 1}",
        "day_of_year": int(moment.strftime("%j")),
        "iso_year": iso_year,
        "iso_week": iso_week,
        "iso_weekday": iso_weekday,
        "timezone_abbreviation": moment.tzname() or "local",
        "utc_offset": format_offset(moment.utcoffset()),
    }


def build_extra_zone(zone_name: str, baseline: dt.datetime) -> dict:
    if ZoneInfo is None:
        return {"zone": zone_name, "error": "zoneinfo unavailable"}

    try:
        target = baseline.astimezone(ZoneInfo(zone_name))
    except Exception as exc:  # pragma: no cover - defensive
        return {"zone": zone_name, "error": str(exc)}

    record = build_time_record(target)
    record["zone"] = zone_name
    return record


def capture_context(extra_zones: list[str]) -> dict:
    local_now = dt.datetime.now().astimezone()
    utc_now = local_now.astimezone(dt.timezone.utc)
    effective_lc_time = os.environ.get("LC_TIME") or os.environ.get("LC_ALL") or os.environ.get("LANG")

    context = {
        "captured_at_unix": int(time.time()),
        "local": build_time_record(local_now),
        "utc": build_time_record(utc_now),
        "timezone": detect_timezone(local_now),
        "extra_zones": [],
        "locale": {
            "LANG": os.environ.get("LANG"),
            "LC_TIME": effective_lc_time,
            "LC_ALL": os.environ.get("LC_ALL"),
        },
        "system": {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
        },
        "session_directives": [
            "Treat the local clock as authoritative for local date and time unless the user specifies another timezone.",
            "Convert relative dates such as today, yesterday, and tomorrow into absolute calendar dates before answering.",
            "Verify volatile external facts live before answering: models, versions, prices, schedules, laws, weather, executives, and current events.",
            "Refresh the temporal anchor when the session crosses midnight, shifts timezone context, or revisits rolling external data.",
        ],
    }

    seen = set()
    for zone_name in extra_zones:
        if zone_name in seen:
            continue
        seen.add(zone_name)
        context["extra_zones"].append(build_extra_zone(zone_name, utc_now))

    return context


def render_markdown(context: dict) -> str:
    lines = [
        "# Temporal Context",
        "",
        f"- Local now: `{context['local']['iso']}`",
        f"- UTC now: `{context['utc']['iso']}`",
        (
            "- Primary timezone: "
            f"`{context['timezone']['primary']}` "
            f"(`{context['timezone']['abbreviation']}`, `{context['timezone']['utc_offset']}`)"
        ),
        (
            "- Locale: "
            f"`LANG={context['locale']['LANG']}` "
            f"`LC_TIME={context['locale']['LC_TIME']}`"
        ),
        "",
    ]

    if context["extra_zones"]:
        lines.extend(["## Extra Zones", ""])
        for zone in context["extra_zones"]:
            if "error" in zone:
                lines.append(f"- `{zone['zone']}`: error `{zone['error']}`")
            else:
                lines.append(f"- `{zone['zone']}`: `{zone['iso']}`")
        lines.append("")

    lines.extend(["## Session Directives", ""])
    for directive in context["session_directives"]:
        lines.append(f"- {directive}")

    return "\n".join(lines)


def render_text(context: dict) -> str:
    lines = [
        f"local={context['local']['iso']}",
        f"utc={context['utc']['iso']}",
        f"timezone={context['timezone']['primary']}",
        f"offset={context['timezone']['utc_offset']}",
    ]
    for zone in context["extra_zones"]:
        if "error" in zone:
            lines.append(f"{zone['zone']}=error:{zone['error']}")
        else:
            lines.append(f"{zone['zone']}={zone['iso']}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--format",
        choices=["json", "markdown", "text"],
        default="json",
        help="Output format.",
    )
    parser.add_argument(
        "--extra-zone",
        action="append",
        default=[],
        help="Additional IANA zone names to include, e.g. America/New_York.",
    )
    args = parser.parse_args()

    context = capture_context(args.extra_zone)

    if args.format == "json":
        json.dump(context, sys.stdout, indent=2)
        sys.stdout.write("\n")
    elif args.format == "markdown":
        sys.stdout.write(render_markdown(context))
        sys.stdout.write("\n")
    else:
        sys.stdout.write(render_text(context))
        sys.stdout.write("\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
