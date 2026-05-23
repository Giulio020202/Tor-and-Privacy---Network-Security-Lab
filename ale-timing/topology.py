from PyQt5.sip import dump
from turtle import delay
import argparse
import signal
import time
from pathlib import Path

from mininet.net import Mininet
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel

# Utility for pcap files
def capture_dir():
    base = Path(__file__).resolve().parent
    target = base / "captures"
    target.mkdir(parents=True, exist_ok=True)
    return target

# tcpdump helpers
def start_tcp_dump(host, intf, filename):
    cmd = f"sudo tcpdump -n -U -i {intf} -w {filename} > /dev/null 2>&1 & echo $!"
    pid = host.cmd(cmd).strip()
    return host, pid

def start_http_demo(client, server):
    server.cmd("mkdir -p /tmp/fake_site")
    server.cmd("cat > /tmp/fake_site/index.html <<'EOF'\n<html><body><h1>Fake Onion Site</h1><p>This page is served by the simulated server.</p></body></html>\nEOF\n")
    http_proc = server.popen(["python3", "-m", "http.server", "8080", "--directory", "/tmp/fake_site"])
    time.sleep(1)
    client_output = client.cmd("python3 -c 'import urllib.request; print(urllib.request.urlopen(\"http://10.0.5.1:8080\").read().decode())'")
    return http_proc, client_output

def parse_ping_avg(output):
    for line in output.splitlines():
        if "min/avg/max" in line or "rtt min/avg/max" in line:
            parts = line.split("=")[-1].strip().split()[0].split("/")
            if len(parts) >= 2:
                return parts[1]
    return None

def run_latency_tests(client1, client2, entry, middle, exit_node, server1, server2):
    measurements = []
    
    hops = [
        (client1, "10.0.5.1", "Client1 -> Server1 (full-path)"),
        (client2, "10.0.6.1", "Client2 -> Server2 (full-path)")
    ]
    for host, target, label in hops:
        output = host.cmd(f"ping -c 4 -q {target}")
        avg = parse_ping_avg(output)
        measurements.append((label, avg, output))
    return measurements

def capture_interfaces():
    return [
        ("client1", "client1-eth0", "client1.pcap"),
        ("client2", "client2-eth0", "client2.pcap"),
        ("entry", "entry-eth0", "entry-from-c1.pcap"),
        ("entry", "entry-eth1", "entry-from-c2.pcap"),
        ("entry", "entry-eth2", "entry-to-middle.pcap"),
        ("middle", "middle-eth0", "middle-in.pcap"),
        ("middle", "middle-eth1", "middle-out.pcap"),
        ("exitnode", "exitnode-eth0", "exitnode-from-middle.pcap"),
        ("exitnode", "exitnode-eth1", "exitnode-to-s1.pcap"),
        ("exitnode", "exitnode-eth2", "exitnode-to-s2.pcap"),
        ("server1", "server1-eth0", "server1.pcap"),
        ("server2", "server2-eth0", "server2.pcap"),
    ]

def run_timing_attack_demo(c1, c2):
    print("\n[nm] Starting timing attack demo...")
    print("[mn] Client 1 sends bursty traffic (5 quick pings, 1.5s pause)...")
    print("[mn] Client 2 sends sparse traffic (2 quick pings, 2.5s pause)...")

    # run pings in background, c1 every 0.2 seconds, c2 every 0.6 seconds
    c1.cmd("sh -c 'while true; do ping -c 5 -i 0.1 10.0.5.1; sleep 1.5; done' > /dev/null 2>&1 &")
    c2.cmd("sh -c 'while true; do ping -c 2 -i 0.1 10.0.6.1; sleep 2.5; done' > /dev/null 2>&1 &")

    print("[mn] Collecting traffic for 15 seconds...")
    time.sleep(15)

    c1.cmd("killall ping")
    c2.cmd("killall ping")
    print("[mn] Traffic generation complete.")

def create_network(capture=False, http_demo=False, test_latency=False, attack=False):
    net = Mininet(link=TCLink, autoSetMacs=True)

    client1 = net.addHost("client1")
    client2 = net.addHost("client2")
    entry = net.addHost("entry")
    middle = net.addHost("middle")
    exit_node = net.addHost("exitnode")
    server1 = net.addHost("server1")
    server2 = net.addHost("server2")

    net.addLink(client1, entry, delay="25ms", jitter="5ms")
    net.addLink(client2, entry, delay="40ms", jitter="10ms")
    net.addLink(entry, middle, delay="50ms", jitter="5ms")
    net.addLink(middle, exit_node, delay="40ms", jitter="5ms")
    net.addLink(exit_node, server1, delay="40ms", jitter="5ms")
    net.addLink(exit_node, server2, delay="20ms", jitter="5ms")

    net.start()

    # client 1
    client1.setIP("10.0.1.1/24")
    entry.setIP("10.0.1.254/24", intf="entry-eth0")

    # client 2
    client2.setIP("10.0.2.1/24")
    entry.setIP("10.0.2.254/24", intf="entry-eth1")

    # entry to middle link
    entry.setIP("10.0.3.1/24", intf="entry-eth2")
    middle.setIP("10.0.3.2/24", intf="middle-eth0")

    # middle to exit link
    middle.setIP("10.0.4.1/24", intf="middle-eth1")
    exit_node.setIP("10.0.4.2/24", intf="exitnode-eth0")

    # exit ro server 1
    exit_node.setIP("10.0.5.254/24", intf="exitnode-eth1")
    server1.setIP("10.0.5.1/24")

    # exit to server 2
    exit_node.setIP("10.0.6.254/24", intf="exitnode-eth2")
    server2.setIP("10.0.6.1/24")

    # clients push traffic to the entry interfaces
    client1.cmd("ip route add default via 10.0.1.254")
    client2.cmd("ip route add default via 10.0.2.254")

    # servers push return traffic to their exit interfaces
    server1.cmd("ip route add default via 10.0.5.254")
    server2.cmd("ip route add default via 10.0.6.254")

    # entry node just pushed everything towards middle
    entry.cmd("ip route add default via 10.0.3.2")

    # exit node just pushes everything back towards middle
    exit_node.cmd("ip route add default via 10.0.4.1")

    # how middle can reach clients
    middle.cmd("ip route add 10.0.1.0/24 via 10.0.3.1")
    middle.cmd("ip route add 10.0.2.0/24 via 10.0.3.1")

    # how middle can reach servers
    middle.cmd("ip route add 10.0.5.0/24 via 10.0.4.2")
    middle.cmd("ip route add 10.0.6.0/24 via 10.0.4.2")

    for relay in [entry, middle, exit_node]:
        relay.cmd("sysctl -w net.ipv4.ip_forward=1")
        relay.cmd("sh -c 'echo 1 > /proc/sys/net/ipv4/ip_forward'")

    print("\nOnion relay path ready:")
    print("  client{1,2} -> entry -> middle -> exitnode -> server{1,2}")
    print("  Use Wireshark/tcpdump on client{1,2}-eth0, entry-eth0/1, middle-eth0/1, exitnode-eth0/1, server{1,2}-eth0")
    print("  Example: sudo wireshark -k -i entry-eth0")

    # if --capture is used, start tcpdump on all nodes
    dump_procs = []
    if capture:
        capture_path = capture_dir()
        print("[mn] Starting tcpdump capture on all path interfaces...")
        for host_name, intf, filename in capture_interfaces():
            host = net.get(host_name)
            output = capture_path / filename
            dump_procs.append(start_tcp_dump(host, intf, output))
        time.sleep(1)
        print(f"[mn] Saved captures to {capture_path}")

    # helper function, if --http-demo is used, start a mockup http server
    http_proc = None
    if http_demo:
        http_proc, client_output = start_http_demo(client1, server1)
        print("[mn] HTTP demo started on server at http://10.0.0.9:8080")
        print("[mn] Client request output:\n", client_output)

    # if --test-latency is used run ping tests
    if test_latency:
        print("\n[mn] Starting latency tests")
        measurements = run_latency_tests(client1, client2, entry, middle, exit_node, server1, server2)
        for label, avg, output in measurements:
            print(f"{label}: avg={avg} ms")
        print("Latency test complete. Use the CLI to inspect hosts or packet captures.")

    if attack:
        run_timing_attack_demo(client1, client2)

    # setup done, start mininet CLI
    CLI(net)

    for host, pid in dump_procs:
        try:
            host.cmd(f"kill {pid}")
        except Exception:
            pass
    if http_proc:
        http_proc.terminate()

    net.stop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Minimal onion relay Mininet topology")
    parser.add_argument("--capture", action="store_true", help="start tcpdump on each path interface")
    parser.add_argument("--http-demo", action="store_true", help="start a fake HTTP server and request a page from the client")
    parser.add_argument("--test-latency", action="store_true", help="measure per-hop and end-to-end latency over the relay path")
    parser.add_argument("--attack", action="store_true", help="generate distinct traffic signatures for a timing attack demo")
    args = parser.parse_args()

    setLogLevel("info")
    create_network(capture=args.capture, http_demo=args.http_demo, test_latency=args.test_latency, attack=args.attack)
