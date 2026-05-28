#!/bin/bash

# Client 1: high frequency packets
CLIENT1_SOCKS="127.0.0.1:9005"
CLIENT1_TARGET="http://127.0.0.1:8080/index"
CLIENT1_BURSTS=5
CLIENT1_SLEEP=2

# Client 2: slow frequency packets
CLIENT2_SOCKS="127.0.0.1:9006"
CLIENT2_TARGET="http://127.0.0.1:8081/index"
CLIENT2_BURSTS=3
CLIENT2_SLEEP=3

# main routing, generate the traffic
simulate_client_traffic() {
    local socks_proxy="$1"
    local target_url="$2"
    local total_bursts="$3"
    local sleep_interval="$4"
    local client_label="$5"

    echo "info: $client_label started ($socks_proxy -> $target_url)"
    
    for ((i=1; i<=total_bursts; i++)); do
        echo "info: $client_label: sending packet $i/$total_bursts..."
        
        # Execute the curl request through the specific Tor SOCKS proxy
        curl --socks5 "$socks_proxy" --silent --show-error "$target_url" > /dev/null
        
        # Only sleep if we aren't on the very last burst
        if [ $i -lt $total_bursts ]; then
            echo "info: $client_label: pausing for ${sleep_interval}s..."
            sleep "$sleep_interval"
        fi
    done
    
    echo "$client_label: all data sent."
}

# entry

# Launch Client 1 in the background
simulate_client_traffic \
    "$CLIENT1_SOCKS" \
    "$CLIENT1_TARGET" \
    "$CLIENT1_BURSTS" \
    "$CLIENT1_SLEEP" \
    "CLIENT_1_FAST" &
PID_CLIENT1=$!

# Launch Client 2 in the background
simulate_client_traffic \
    "$CLIENT2_SOCKS" \
    "$CLIENT2_TARGET" \
    "$CLIENT2_BURSTS" \
    "$CLIENT2_SLEEP" \
    "CLIENT_2_SLOW" &
PID_CLIENT2=$!

echo "Started curl processes (PIDs: $PID_CLIENT1, $PID_CLIENT2)"

# Wait actively until both background traffic loops terminate
wait $PID_CLIENT1 $PID_CLIENT2
