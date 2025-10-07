#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INPUT_JSON="$SCRIPT_DIR/wydarzenia.json"
FILTERED_JSON="$SCRIPT_DIR/filtered_wydarzenia.json"
OUTPUT_ICS="$SCRIPT_DIR/plan.ics"
CAL_NAME=""
URL=""

usage() {
  echo "Usage: $0 --faculty <FAC> --lk <LKx> --l <Lx> --p <Px> [--url <endpoint>] [--input <path>] [--filtered <path>] [--output <path>] [--name <calendar name>]" 1>&2
}

FACULTY=""
LK_GROUP=""
L_GROUP=""
P_GROUP=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --faculty)
      FACULTY="$2"; shift 2 ;;
    --lk)
      LK_GROUP="$2"; shift 2 ;;
    --l)
      L_GROUP="$2"; shift 2 ;;
    --p)
      P_GROUP="$2"; shift 2 ;;
    --url)
      URL="$2"; shift 2 ;;
    --input)
      INPUT_JSON="$2"; shift 2 ;;
    --filtered)
      FILTERED_JSON="$2"; shift 2 ;;
    --output)
      OUTPUT_ICS="$2"; shift 2 ;;
    --name)
      CAL_NAME="$2"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown argument: $1" 1>&2; usage; exit 1 ;;
  esac
done

if [[ -z "$FACULTY" || -z "$LK_GROUP" || -z "$L_GROUP" || -z "$P_GROUP" ]]; then
  echo "Missing required arguments." 1>&2
  usage
  exit 1
fi

if [[ -z "$CAL_NAME" ]]; then
  CAL_NAME="Plan $FACULTY $LK_GROUP $L_GROUP $P_GROUP"
fi

FILTER_CMD=(python3 "$SCRIPT_DIR/filter_events.py" --output "$FILTERED_JSON" --faculty "$FACULTY" --lk "$LK_GROUP" --l "$L_GROUP" --p "$P_GROUP")
if [[ -n "$URL" ]]; then
  FILTER_CMD+=(--url "$URL")
else
  FILTER_CMD+=(--input "$INPUT_JSON")
fi

echo "[1/2] Filtering events -> $FILTERED_JSON"
"${FILTER_CMD[@]}"

echo "[2/2] Generating ICS -> $OUTPUT_ICS"
python3 "$SCRIPT_DIR/json_to_ics.py" \
  --input "$FILTERED_JSON" \
  --output "$OUTPUT_ICS" \
  --calendar-name "$CAL_NAME"

echo "Done. Calendar: $OUTPUT_ICS"


