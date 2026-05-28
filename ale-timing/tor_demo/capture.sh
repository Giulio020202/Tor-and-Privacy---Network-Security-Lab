#!/bin/bash

# Config vars
INTERFACE="lo" # loopback

# define ports as arrays
INGRESS_PORTS=("9005" "9006")
EGRESS_PORTS=("8080" "8081")

# output files
INGRESS_PCAP="ingress.pcap"
EGRESS_PCAP="egress.pcap"

# helper: build tcpdump filter string
build_filter() {
    local ports=("$@")
    local filter=""
    for i in "${!ports[@]}"; do
        if [ $i -eq 0 ]; then
            filter="port ${ports[$i]}"
        else
            filter="$filter or port ${ports[$i]}"
        fi
    done
    echo "$filter"
}

# execution
INGRESS_FILTER=$(build_filter "${INGRESS_PORTS[@]}")
EGRESS_FILTER=$(build_filter "${EGRESS_PORTS[@]}")

echo "[info] Starting Ingress Capture: $INGRESS_FILTER"
tcpdump -i "$INTERFACE" -n -U "$INGRESS_FILTER" -w "$INGRESS_PCAP" 2>/dev/null &
INGRESS_PID=$!

echo "[info] Starting Egress Capture: $EGRESS_FILTER"
tcpdump -i "$INTERFACE" -n -U "$EGRESS_FILTER" -w "$EGRESS_PCAP" 2>/dev/null &
EGRESS_PID=$!

echo "------------------------------------------------"
echo "[i] Captures are running in the background."
echo "    Ingress PID: $INGRESS_PID"
echo "    Egress PID:  $EGRESS_PID"
echo "------------------------------------------------"
echo "[n] Open another terminal and generate your curl traffic now."
echo "[n] Press [CTRL+C] in this terminal when finished to stop captures."

# trap CTRL+C to kill jobs cleanly
trap "echo -e '\n[info] Stopping captures...'; kill $INGRESS_PID $EGRESS_PID; exit 0" INT

# wait until CTRL+C is pressed
wait
