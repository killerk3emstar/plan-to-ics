#!/usr/bin/env python3
import argparse
import json
import os
import sys
from urllib.request import urlopen
from urllib.error import URLError, HTTPError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Filter schedule events by faculty and group prefix (LK/L/P). "
            "Lectures (group 'W') are always included."
        )
    )
    parser.add_argument(
        "--input",
        default="wydarzenia.json",
        help="Path to input JSON with events (default: wydarzenia.json)",
    )
    parser.add_argument(
        "--url",
        help="If provided, fetch events JSON from this URL instead of --input",
    )
    parser.add_argument(
        "--output",
        default="filtered_wydarzenia.json",
        help="Path to write filtered JSON (default: filtered_wydarzenia.json)",
    )
    parser.add_argument(
        "--faculty",
        required=True,
        help="Exact faculty code to include (e.g., IwIKs1)",
    )
    parser.add_argument(
        "--lk",
        required=True,
        help="Exact LK group (e.g., LK2)",
    )
    parser.add_argument(
        "--l",
        required=True,
        help="Exact L group (e.g., L3)",
    )
    parser.add_argument(
        "--p",
        required=True,
        help="Exact P group (e.g., P4)",
    )
    return parser.parse_args()


def load_json_from_file(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_json_from_url(url: str):
    try:
        with urlopen(url) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            data = resp.read().decode(charset)
            return json.loads(data)
    except (URLError, HTTPError) as e:
        raise RuntimeError(f"Failed to fetch URL {url}: {e}")


def save_json(path: str, data) -> None:
    # Preserve readability with indent and stable key order
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4, sort_keys=False)


def _tokenize_groups(raw: str) -> list[str]:
    if not raw:
        return []
    tokens: list[str] = []
    for part in raw.replace(",", "/").split("/"):
        token = part.strip()
        if token:
            tokens.append(token)
    return tokens


def should_include_event(event: dict, selected_faculty: str, lk_group: str, l_group: str, p_group: str) -> bool:
    faculty = event.get("faculty")
    if faculty != selected_faculty:
        return False

    group_value = (event.get("group") or "").strip()
    tokens = _tokenize_groups(group_value)
    if not tokens:
        return False

    # Always include lectures when any token equals 'W' (case-insensitive exact 'W')
    if any(tok.upper() == "W" for tok in tokens):
        return True

    wanted = {lk_group.lower(), l_group.lower(), p_group.lower()}
    return any(tok.lower() in wanted for tok in tokens)


def main() -> int:
    args = parse_args()

    # Load data from URL if provided, otherwise from file
    try:
        if args.url:
            data = load_json_from_url(args.url)
        else:
            if not os.path.exists(args.input):
                print(f"Input file not found: {args.input}", file=sys.stderr)
                return 1
            data = load_json_from_file(args.input)
    except Exception as e:
        print(f"Failed to load events: {e}", file=sys.stderr)
        return 1

    # The expected structure is a dict mapping event ids to event objects.
    # If it's a list, convert to a dict with synthetic keys to preserve shape.
    if isinstance(data, list):
        source_items = {str(i): item for i, item in enumerate(data)}
    elif isinstance(data, dict):
        source_items = data
    else:
        print("Unsupported JSON structure. Expected object or array.", file=sys.stderr)
        return 1

    filtered = {}
    included_count = 0
    for key, event in source_items.items():
        if not isinstance(event, dict):
            # Skip malformed entries
            continue
        if should_include_event(event, args.faculty, args.lk, args.l, args.p):
            filtered[key] = event
            included_count += 1

    save_json(args.output, filtered)

    total = len(source_items)
    print(
        f"Filtered {included_count}/{total} events for faculty='{args.faculty}' (groups: {args.lk}, {args.l}, {args.p}; lectures included).\n"
        f"Output written to: {args.output}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


