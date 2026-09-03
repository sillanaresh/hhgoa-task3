#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTEXT_DIR="$PROJECT_DIR/.context"
INPUT_DIR="$CONTEXT_DIR/input"
DESTINATION="$INPUT_DIR/sundar-pichai-cc-by-4.jpg"
SOURCE_URL='https://commons.wikimedia.org/wiki/Special:Redirect/file/Sundar_Pichai_%282023%29_cropped.jpg'
EXPECTED_SHA256='eff1772fe7c4c06e4a5e02d57dc16008329cb2e8f28047e3a8f335ad955aa0ba'

sha256_file() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    echo "A SHA-256 command is required to verify the demo image." >&2
    exit 1
  fi
}

mkdir -p "$INPUT_DIR"
chmod 700 "$CONTEXT_DIR"
chmod 700 "$INPUT_DIR"

if [[ -f "$DESTINATION" ]]; then
  EXISTING_SHA256="$(sha256_file "$DESTINATION")"
  if [[ "$EXISTING_SHA256" == "$EXPECTED_SHA256" ]]; then
    chmod 600 "$DESTINATION"
    echo "Demo input is ready: $DESTINATION"
    exit 0
  fi
fi

TASK_TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TASK_TEMP_DIR"' EXIT
DOWNLOAD="$TASK_TEMP_DIR/sundar-pichai.jpg"

curl --fail --location --silent --show-error "$SOURCE_URL" --output "$DOWNLOAD"
ACTUAL_SHA256="$(sha256_file "$DOWNLOAD")"
if [[ "$ACTUAL_SHA256" != "$EXPECTED_SHA256" ]]; then
  echo "Demo image checksum changed. Refusing to use an unreviewed file." >&2
  exit 1
fi

install -m 600 "$DOWNLOAD" "$DESTINATION"
echo "Demo input is ready: $DESTINATION"
