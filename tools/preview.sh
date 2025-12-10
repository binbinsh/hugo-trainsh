#!/usr/bin/env bash
set -euo pipefail

# Generate 3:2 preview images (1500x1000 and 900x600) from a source screenshot.
# Requires ImageMagick (magick or convert).

usage() {
  cat <<'EOF'
Usage: bash tools/preview.sh <src> [--out images/screenshot.png] [--tn images/tn.png] [--gravity top|center|bottom]

Arguments:
  src               Source screenshot image (any format ImageMagick supports)

Options:
  --out PATH        Output path for 1500x1000 image (default: images/screenshot.png)
  --tn PATH         Output path for 900x600 thumbnail (default: images/tn.png)
  --gravity VALUE   Crop anchor: top | center | bottom (default: top)
  -h, --help        Show this help
EOF
}

OUT="images/screenshot.png"
TN="images/tn.png"
GRAVITY="top"
SRC=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out)
      OUT="$2"
      shift 2
      ;;
    --tn)
      TN="$2"
      shift 2
      ;;
    --gravity)
      GRAVITY="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      if [[ -z "$SRC" ]]; then
        SRC="$1"
        shift
      else
        echo "Unexpected argument: $1" >&2
        usage
        exit 1
      fi
      ;;
  esac
done

if [[ -z "$SRC" ]]; then
  usage
  exit 1
fi

case "$GRAVITY" in
  top) im_gravity="North" ;;
  center) im_gravity="Center" ;;
  bottom) im_gravity="South" ;;
  *)
    echo "Invalid gravity: $GRAVITY (choose top|center|bottom)" >&2
    exit 1
    ;;
esac

if command -v magick >/dev/null 2>&1; then
  convert_cmd=(magick)
elif command -v convert >/dev/null 2>&1; then
  convert_cmd=(convert)
else
  echo "ImageMagick is required (magick or convert not found)." >&2
  exit 1
fi

mkdir -p "$(dirname "$OUT")" "$(dirname "$TN")"

run_convert() {
  local width="$1" height="$2" dest="$3"
  "${convert_cmd[@]}" "$SRC" -auto-orient -resize "${width}x${height}^" \
    -gravity "$im_gravity" -extent "${width}x${height}" "$dest"
}

run_convert 1500 1000 "$OUT"
run_convert 900 600 "$TN"

echo "Wrote $OUT and $TN"
