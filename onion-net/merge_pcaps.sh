#!/usr/bin/env bash
set -euo pipefail

CAPTURE_DIR="captures"
OUTPUT_FILE="${1:-${CAPTURE_DIR}/all-captures.pcap}"

if ! command -v mergecap >/dev/null 2>&1; then
  echo "Error: mergecap is not installed. Install Wireshark or tshark tools and try again." >&2
  exit 1
fi

mkdir -p "$CAPTURE_DIR"

readarray -t pcap_files < <(find "$CAPTURE_DIR" -maxdepth 1 -type f -name '*.pcap' | sort)
if [ "${#pcap_files[@]}" -eq 0 ]; then
  echo "No PCAP files found in $CAPTURE_DIR" >&2
  exit 1
fi

mergecap -w "$OUTPUT_FILE" "${pcap_files[@]}"

echo "Merged ${#pcap_files[@]} PCAP file(s) into $OUTPUT_FILE"
