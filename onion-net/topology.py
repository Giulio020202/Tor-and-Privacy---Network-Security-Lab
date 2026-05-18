import argparse
import signal
import time
from pathlib import Path

from mininet.net import Mininet
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel

# utility function for pcap files managemnet
def capture_dir():
    base = Path(__file__).resolve().parent
    target = base / "captures"
    target.mkdir(parents=True, exist_ok=True)
    return target

# helper functions for running tcpdump on each node
def start_tcpdump(host, intf, filename):
    cmd = ["tcpdump", "-n", "-U", "-s", "0", "-i", intf, "-w", str(filename)]
    return host.popen(cmd)

def start_http_demo(client, server):
    server.cmd("mkdir -p /tmp/fake_site")
    server.cmd("cat > /tmp/fake_site/index.html <<'EOF'\n<html><body><h1>Fake Onion Site</h1><p>This page is served by the simulated server.</p></body></html>\nEOF\n")
    http_proc = server.popen(["python3", "-m", "http.server", "8080", "--directory", "/tmp/fake_site"])
    time.sleep(1)
    client_output = client.cmd("python3 -c 'import urllib.request; print(urllib.request.urlopen(\"http://10.0.0.7:8080\").read().decode())'")
    return http_proc, client_output


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
        (client, "10.0.0.1", "client->entry"),
        (entry, "10.0.0.3", "entry->middle"),
        (middle, "10.0.0.5", "middle->exitnode"),
        (exit_node, "10.0.0.7", "exitnode->server"),
        (client, "10.0.0.7", "client->server (full path)"),
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
def create_network(capture=False, http_demo=False, test_latency=False):
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

    # helper function, if --http-demo is used, start a mockup http server
    http_proc = None
    if http_demo:
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

    # cleanup on exit, if doesn work use "sudo mn -c" to clean up manually
    for proc in dump_procs:
        try:
            proc.send_signal(signal.SIGINT)
            proc.wait(timeout=5)
        except Exception:
            proc.terminate()
    if http_proc:
        http_proc.terminate()

    net.stop()


if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="Minimal onion relay Mininet topology")
    parser.add_argument("--capture", action="store_true", help="start tcpdump on each path interface")
    parser.add_argument("--http-demo", action="store_true", help="start a fake HTTP server and request a page from the client")
    parser.add_argument("--test-latency", action="store_true", help="measure per-hop and end-to-end latency over the relay path")
    args = parser.parse_args()

    setLogLevel("info") 
    create_network(capture=args.capture, http_demo=args.http_demo, test_latency=args.test_latency)
