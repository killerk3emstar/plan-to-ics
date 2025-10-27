#!/usr/bin/env python3
import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Optional, List


APPLE_PRODID = "-//pz//json-to-ics//EN"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert filtered schedule JSON to Apple Calendar compatible .ics file."
        )
    )
    parser.add_argument(
        "--input",
        default="filtered_wydarzenia.json",
        help="Path to input filtered events JSON (default: filtered_wydarzenia.json)",
    )
    parser.add_argument(
        "--output",
        default="plan.ics",
        help="Path to output .ics file (default: plan.ics)",
    )
    parser.add_argument(
        "--calendar-name",
        default="Plan zajec",
        help="VCALENDAR NAME/X-WR-CALNAME (default: Plan zajec)",
    )
    parser.add_argument(
        "--tz",
        default="Europe/Warsaw",
        help="Timezone for naive input datetimes (default: Europe/Warsaw)",
    )
    parser.add_argument(
        "--use-tzid",
        action="store_true",
        help="Use TZID in DTSTART/DTEND instead of UTC (better for DST-aware calendars)",
    )
    return parser.parse_args()


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_dict(data):
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        return {str(i): v for i, v in enumerate(data)}
    raise ValueError("Unsupported JSON structure; expected object or array")


def parse_iso_with_tzid(dt_str: str, tz: ZoneInfo, tzid: str) -> tuple[str, str]:
    """Returns (DTSTART value, TZID if needed) or (UTC value, None)"""
    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    
    # For calendar apps like Apple Calendar: use TZID form instead of UTC
    local_dt_str = dt.strftime("%Y%m%dT%H%M%S")
    return local_dt_str, tzid


def parse_iso_as_utc_z(dt_str: str, naive_tz: ZoneInfo) -> str:
    # Accept both naive and offset-aware ISO, normalize to UTC and format as YYYYMMDDTHHMMSSZ
    # Example input: 2025-10-06T09:15:00 or 2025-10-06T09:15:00+02:00
    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=naive_tz)
    dt_utc = dt.astimezone(timezone.utc)
    return dt_utc.strftime("%Y%m%dT%H%M%SZ")


def parse_date_as_utc_z(date_str: str, naive_tz: ZoneInfo) -> str:
    # For UNTIL when provided as date or datetime string
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=naive_tz)
        dt_utc = dt.astimezone(timezone.utc)
        return dt_utc.strftime("%Y%m%dT%H%M%SZ")
    except Exception:
        # Try date-only
        dt = datetime.fromisoformat(date_str)
        dt = dt.replace(tzinfo=naive_tz)
        return dt.strftime("%Y%m%dT%H%M%SZ")


def build_rrule(event: dict, naive_tz: ZoneInfo) -> Optional[str]:
    r = event.get("rrule")
    if not isinstance(r, dict):
        return None
    freq = r.get("freq")
    interval = r.get("interval")
    until = r.get("until")
    parts = []
    if freq:
        parts.append(f"FREQ={freq.upper()}")
    if interval:
        parts.append(f"INTERVAL={int(interval)}")
    if until:
        parts.append(f"UNTIL={parse_date_as_utc_z(until, naive_tz)}")
    return ";".join(parts) if parts else None


def escape_text(value: str) -> str:
    # RFC5545 escaping: backslash, comma, semicolon, and newlines
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def build_vtimezone(tzid: str, tz: ZoneInfo) -> List[str]:
    """Generate minimal VTIMEZONE block for Europe/Warsaw"""
    lines = [
        "BEGIN:VTIMEZONE",
        f"TZID:{tzid}",
        "BEGIN:STANDARD",
        "DTSTART:20230326T030000",
        "TZOFFSETFROM:+0100",
        "TZOFFSETTO:+0100",
        "TZNAME:CET",
        "END:STANDARD",
        "BEGIN:DAYLIGHT",
        "DTSTART:20230326T020000",
        "TZOFFSETFROM:+0100",
        "TZOFFSETTO:+0200",
        "TZNAME:CEST",
        "END:DAYLIGHT",
        "END:VTIMEZONE",
    ]
    return lines


def build_event(uid_namespace: str, key: str, event: dict, naive_tz: ZoneInfo, use_tzid: bool = False, tzid: str = "") -> List[str]:
    lines: List[str] = ["BEGIN:VEVENT"]

    # UID should be stable across regenerations if input key persists
    uid = f"{key}@{uid_namespace}"
    lines.append(f"UID:{uid}")

    # DTSTAMP should be generation time in UTC
    dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines.append(f"DTSTAMP:{dtstamp}")

    # DTSTART/DTEND
    start = event.get("start")
    end = event.get("end")
    if start:
        if use_tzid:
            start_val, start_tzid = parse_iso_with_tzid(start, naive_tz, tzid)
            lines.append(f"DTSTART;TZID={start_tzid}:{start_val}")
        else:
            lines.append(f"DTSTART:{parse_iso_as_utc_z(start, naive_tz)}")
    if end:
        if use_tzid:
            end_val, end_tzid = parse_iso_with_tzid(end, naive_tz, tzid)
            lines.append(f"DTEND;TZID={end_tzid}:{end_val}")
        else:
            lines.append(f"DTEND:{parse_iso_as_utc_z(end, naive_tz)}")

    # SUMMARY, LOCATION, DESCRIPTION
    title = event.get("eventType") or event.get("title") or "Zajecia"
    group = event.get("group") or ""
    instructor = event.get("instructor") or ""
    faculty = event.get("faculty") or ""
    room = event.get("room") or ""

    summary = f"{title} ({group})"
    lines.append(f"SUMMARY:{escape_text(summary)}")
    if room:
        lines.append(f"LOCATION:{escape_text(room)}")

    description_parts = []
    if instructor:
        description_parts.append(f"Prowadzacy: {instructor}")
    if faculty:
        description_parts.append(f"Faculty: {faculty}")
    if description_parts:
        desc = "\n".join(description_parts)
        lines.append(f"DESCRIPTION:{escape_text(desc)}")

    # RRULE
    rrule = build_rrule(event, naive_tz)
    if rrule:
        lines.append(f"RRULE:{rrule}")

    lines.append("END:VEVENT")
    return lines


def write_ics(path: str, calendar_name: str, events: List[List[str]], vtimezone: Optional[List[str]] = None) -> None:
    lines: List[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{APPLE_PRODID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_text(calendar_name)}",
        f"NAME:{escape_text(calendar_name)}",
    ]
    if vtimezone:
        lines.extend(vtimezone)
    for ev in events:
        lines.extend(ev)
    lines.append("END:VCALENDAR")

    # Apple Calendar tolerates LF; CRLF is more traditional but not required here.
    content = "\n".join(lines) + "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def main() -> int:
    args = parse_args()
    if not os.path.exists(args.input):
        print(f"Input not found: {args.input}", file=sys.stderr)
        return 1

    try:
        data = load_json(args.input)
        items = ensure_dict(data)
    except Exception as e:
        print(f"Failed to load input JSON: {e}", file=sys.stderr)
        return 1

    # Use a stable namespace for UIDs derived from output path
    uid_namespace = uuid.uuid5(uuid.NAMESPACE_URL, os.path.abspath(args.input)).hex

    try:
        naive_tz = ZoneInfo(args.tz)
    except Exception:
        print(f"Invalid timezone '{args.tz}', falling back to UTC", file=sys.stderr)
        naive_tz = ZoneInfo("UTC")

    # Build VTIMEZONE if using TZID
    vtimezone: Optional[List[str]] = None
    if args.use_tzid:
        vtimezone = build_vtimezone(args.tz, naive_tz)

    events: List[List[str]] = []
    for key, ev in items.items():
        if not isinstance(ev, dict):
            continue
        events.append(build_event(uid_namespace, key, ev, naive_tz, args.use_tzid, args.tz))

    write_ics(args.output, args.calendar_name, events, vtimezone)

    print(f"Wrote {len(events)} events to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


