import argparse
import signal
import subprocess
import threading
import time
from pathlib import Path

from mininet.net import Mininet
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel

# utility function for pcap files management
def capture_dir():
    base = Path(__file__).resolve().parent
    target = base / "captures"
    target.mkdir(parents=True, exist_ok=True)
    return target

# helper functions for running tcpdump on each node
def start_tcpdump(host, intf, filename):
    # --immediate-mode flushes each packet to disk as it arrives (same as -U,
    # but explicit). This ensures the pcap file is always in a consistent state
    # and is not left with partial packet data if the process is stopped.
    cmd = ["tcpdump", "-n", "--immediate-mode", "-s", "0", "-i", intf, "-w", str(filename)]
    return host.popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def stop_tcpdump_procs(dump_procs, timeout=8):
    """
    Gracefully stop tcpdump processes so pcap files are properly finalised.

    Strategy: send SIGINT (which makes tcpdump flush and write the file
    trailer), wait up to `timeout` seconds, then fall back to SIGTERM.
    We never send SIGKILL — that cuts the file mid-write and produces the
    'damaged or corrupt' error seen by mergecap/Wireshark.
    """
    for proc in dump_procs:
        try:
            proc.send_signal(signal.SIGINT)
        except Exception:
            pass

    deadline = time.time() + timeout
    for proc in dump_procs:
        remaining = max(0.5, deadline - time.time())
        try:
            proc.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            print("[mn] WARNING: tcpdump did not exit after SIGINT; sending SIGTERM")
            try:
                proc.send_signal(signal.SIGTERM)
                proc.wait(timeout=3)
            except Exception:
                pass  # accept a possibly truncated capture rather than corrupting it with SIGKILL


def start_http_demo(client, server):
    site_dir = Path(__file__).resolve().parent / "site"
    http_proc = server.popen(["python3", "-m", "http.server", "8080", "--directory", str(site_dir)])
    time.sleep(1)
    client_output = client.cmd("python3 -c 'import urllib.request; print(urllib.request.urlopen(\"http://10.0.0.7:8080\").read().decode())'")
    return http_proc, client_output


def start_onion_demo(client, entry, middle, exit_node, server):
    script_path = Path(__file__).resolve().parent / "onion_comm.py"
    site_dir = Path(__file__).resolve().parent / "site"
    http_proc = server.popen(["python3", "-m", "http.server", "8080", "--directory", str(site_dir)])

    relays = [
        (entry, "entry", "10.0.0.1", 9001),
        (middle, "middle", "10.0.0.3", 9002),
        (exit_node, "exit", "10.0.0.5", 9003),
    ]
    relay_procs = []
    relay_logs = {}

    def stream_relay_output(name, proc, output_list):
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            try:
                text = line.decode("utf-8", errors="ignore")
            except Exception:
                text = str(line)
            print(f"[{name}] {text.rstrip()}")
            output_list.append(text)

    for host, key, ip, port in relays:
        cmd = [
            "python3",
            str(script_path),
            "--mode",
            "relay",
            "--key",
            key,
            "--listen-ip",
            ip,
            "--listen-port",
            str(port),
            "--server-ip",
            "10.0.0.7",
            "--server-port",
            "8080",
        ]
        proc = host.popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        relay_output = []
        thread = threading.Thread(target=stream_relay_output, args=(key, proc, relay_output), daemon=True)
        thread.start()
        relay_procs.append((host, proc, thread))
        relay_logs[key] = relay_output

    time.sleep(1)

    client_output = client.cmd(f"python3 {script_path} --mode client --entry-ip 10.0.0.1 --entry-port 9001 --path /")
    print("[mn] Onion demo: request sent from client")

    success = False
    time.sleep(1)
    for _ in range(5):
        for outputs in relay_logs.values():
            if any("EXIT node received request" in line for line in outputs):
                success = True
                break
        if success:
            break
        time.sleep(1)

    if success:
        print("[mn] Onion demo: response received by exit relay")
    else:
        print("[mn] Onion demo: response not detected")

    return http_proc, relay_procs, client_output, success


def start_tor_demo(server, capture=False):
    """
    Spin up a real Tor network via chutney (fully local, no internet needed),
    start the Mininet HTTP server so the Tor exit node can reach it, then
    send one GET request through the Tor circuit.

    The exit node will forward unencrypted HTTP to server_ip:8080 on the
    Mininet network, so students can compare:
      - loopback capture (tor_loopback.pcap) → TLS-wrapped Tor cells
      - server-eth0 capture                  → plain HTTP, no source IP info
    """
    try:
        from tor_chutney import TorChutneyDemo
    except ImportError as exc:
        print(f"[mn] Cannot import tor_chutney: {exc}")
        return None, None

    site_dir = Path(__file__).resolve().parent / "site"
    http_proc = server.popen(
        ["python3", "-m", "http.server", "8080", "--directory", str(site_dir)]
    )
    time.sleep(1)

    demo = TorChutneyDemo(
        server_ip="10.0.0.7",
        server_port=8080,
        capture=capture,
        capture_dir=capture_dir(),
    )
    try:
        demo.start()
        response = demo.run_request(path="/")
        print("[mn] Tor demo complete.")
        print("[mn] Teaching notes:")
        print("     - Open captures/tor_loopback.pcap in Wireshark")
        print("       Filter: 'ssl' or 'tls' – you will see TLS records, not readable HTTP.")
        print("     - Open captures/server-eth0.pcap (if --capture was also passed)")
        print("       Filter: 'http' – you will see plain GET / from the Tor exit IP.")
        print("     - Compare with the toy-XOR onion demo: same layered idea,")
        print("       but real Tor uses TLS + Diffie-Hellman instead of fixed XOR keys.")
        return http_proc, demo
    except Exception as exc:
        print(f"[mn] Tor demo failed: {exc}")
        demo.stop()
        return http_proc, None


def parse_ping_avg(output):
    for line in output.splitlines():
        if "min/avg/max" in line or "rtt min/avg/max" in line:
            parts = line.split("=")[-1].strip().split()[0].split("/")
            if len(parts) >= 2:
                return parts[1]
    return None


def run_latency_tests(client, entry, middle, exit_node, server):
    measurements = []
    hops = [
        (client, "10.0.0.1", "[client] -> [entry]"),
        (entry, "10.0.0.3", "[entry] -> [middle]"),
        (middle, "10.0.0.5", "[middle] -> [exitnode]"),
        (exit_node, "10.0.0.7", "[exitnode] -> [server]"),
        (client, "10.0.0.7", "[client] -> [server] (full path)"),
    ]
    for host, target, label in hops:
        output = host.cmd(f"ping -c 4 -q {target}")
        avg = parse_ping_avg(output)
        measurements.append((label, avg, output))
    return measurements


def capture_interfaces():
    return [
        ("client", "client-eth0", "client-eth0.pcap"),
        ("entry", "entry-eth0", "entry-eth0.pcap"),
        ("entry", "entry-eth1", "entry-eth1.pcap"),
        ("middle", "middle-eth0", "middle-eth0.pcap"),
        ("middle", "middle-eth1", "middle-eth1.pcap"),
        ("exitnode", "exitnode-eth0", "exitnode-eth0.pcap"),
        ("exitnode", "exitnode-eth1", "exitnode-eth1.pcap"),
        ("server", "server-eth0", "server-eth0.pcap"),
    ]


# actual network setup and startup
def create_network(capture=False, http_demo=False, test_latency=False, onion_demo=False, tor_demo=False):
    net = Mininet(link=TCLink, autoSetMacs=True)

    # create nodes
    client = net.addHost("client")
    entry = net.addHost("entry")
    middle = net.addHost("middle")
    exit_node = net.addHost("exitnode")
    server = net.addHost("server")

    # create links between nodes with simulated latency
    net.addLink(client, entry, delay="25ms", jitter="5ms")
    net.addLink(entry, middle, delay="40ms", jitter="5ms")
    net.addLink(middle, exit_node, delay="35ms", jitter="5ms")
    net.addLink(exit_node, server, delay="25ms", jitter="5ms")

    # start the network
    net.start()

    # set ips and routes
    #TODO: make slides about the network topology and IP scheme to explain this part better
    client.setIP("10.0.0.0/31")
    entry.setIP("10.0.0.1/31", intf="entry-eth0")
    entry.setIP("10.0.0.2/31", intf="entry-eth1")
    middle.setIP("10.0.0.3/31", intf="middle-eth0")
    middle.setIP("10.0.0.4/31", intf="middle-eth1")
    exit_node.setIP("10.0.0.5/31", intf="exitnode-eth0")
    exit_node.setIP("10.0.0.6/31", intf="exitnode-eth1")
    server.setIP("10.0.0.7/31")

    client.cmd("ip route add default via 10.0.0.1")
    entry.cmd("ip route add default via 10.0.0.3")
    middle.cmd("ip route add 10.0.0.0/30 via 10.0.0.2")
    middle.cmd("ip route add default via 10.0.0.5")
    exit_node.cmd("ip route add 10.0.0.0/30 via 10.0.0.4")
    server.cmd("ip route add default via 10.0.0.6")

    # enable IP forwarding on the relay nodes, otherwise they just listen and drop
    for relay in [entry, middle, exit_node]:
        relay.cmd("sysctl -w net.ipv4.ip_forward=1")
        relay.cmd("sh -c 'echo 1 > /proc/sys/net/ipv4/ip_forward'")

    print("\nOnion relay path ready:")
    print("  client -> entry -> middle -> exitnode -> server")
    print("  Use Wireshark/tcpdump on client-eth0, entry-eth0/eth1, middle-eth0/eth1, exitnode-eth0/eth1, server-eth0")
    print("  Example: sudo wireshark -k -i entry-eth0")

    # if --capture is used, start tcpdump on all nodes
    dump_procs = []
    if capture:
        capture_path = capture_dir()
        print("[mn] Starting tcpdump capture on all path interfaces...")
        for host_name, intf, filename in capture_interfaces():
            host = net.get(host_name)
            output = capture_path / filename
            dump_procs.append(start_tcpdump(host, intf, output))
        time.sleep(1)   # this shouldnt be necessary, but without it the captures sometimes are empty
        print(f"[mn] Saved captures to {capture_path}/")

    # helper processes and demo mode support
    http_proc = None
    relay_info = []
    tor_demo_obj = None

    if tor_demo:
        # Real Tor via chutney – runs on the host's loopback, not inside Mininet.
        # The Mininet server at 10.0.0.7:8080 acts as the destination; the Tor
        # exit node reaches it via the Mininet routing table.
        print("\n[mn] Starting Tor demo (chutney) …")
        print("[mn] NOTE: chutney bootstrapping takes ~30 s – please wait.")
        http_proc, tor_demo_obj = start_tor_demo(server, capture=capture)
    elif onion_demo:
        http_proc, relay_info, client_output, success = start_onion_demo(client, entry, middle, exit_node, server)
        status = "OK" if success else "FAIL"
        print(f"[mn] Onion demo completed (status: {status})")
        print("[mn] Client output:\n", client_output)
    elif http_demo:
        http_proc, client_output = start_http_demo(client, server)
        print("[mn] HTTP demo started on server at http://10.0.0.7:8080")
        print("[mn] Client request output:\n", client_output)

    # if --test-latency is used, run ping tests
    if test_latency:
        print("\n[mn] Starting latency tests")
        measurements = run_latency_tests(client, entry, middle, exit_node, server)
        for label, avg, output in measurements:
            print(f"{label}: avg={avg} ms")
        print("Latency test complete. Use the CLI to inspect hosts or packet captures.")

    # setup done, start mininet CLI
    CLI(net)

    # ---- cleanup ----------------------------------------------------------
    # Order matters:
    #   1. Stop tcpdump FIRST, while interfaces still exist, so it can flush
    #      and write the pcap file trailer correctly.
    #   2. Stop relay/demo processes.
    #   3. Stop the Mininet network last (tears down interfaces).

    if dump_procs:
        print("[mn] Stopping tcpdump captures (waiting for flush)...")
        stop_tcpdump_procs(dump_procs)
        print("[mn] Captures finalised.")

    for host, proc, thread in relay_info:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            try:
                if hasattr(proc, 'pid'):
                    host.cmd(f"kill -9 {proc.pid} 2>/dev/null || true")
            except Exception:
                pass
        try:
            thread.join(timeout=1)
        except Exception:
            pass

    if tor_demo_obj is not None:
        tor_demo_obj.stop()

    if http_proc:
        http_proc.terminate()

    net.stop()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Minimal onion relay Mininet topology")
    parser.add_argument("--capture", action="store_true", help="start tcpdump on each path interface")
    parser.add_argument("--http-demo", action="store_true", help="start a fake HTTP server and request a page from the client")
    parser.add_argument("--test-latency", action="store_true", help="measure per-hop and end-to-end latency over the relay path")
    parser.add_argument("--onion-demo", action="store_true", help="run a minimal layered onion request through entry/middle/exit")
    parser.add_argument(
        "--tor-demo",
        action="store_true",
        help=(
            "spin up a real Tor network via chutney (fully local, no internet), "
            "send a request to the Mininet HTTP server through it, and optionally "
            "capture traffic for Wireshark comparison (combine with --capture)"
        ),
    )
    args = parser.parse_args()

    setLogLevel("info")
    create_network(
        capture=args.capture,
        http_demo=args.http_demo,
        test_latency=args.test_latency,
        onion_demo=args.onion_demo,
        tor_demo=args.tor_demo,
    )
