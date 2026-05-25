import os
import time
import subprocess
from pathlib import Path
from mininet.net import Mininet
from mininet.node import OVSController
from mininet.cli import CLI
from mininet.log import setLogLevel, info

# run mininet as root
# need the user who ran sudo to run the tor process
SUDO_USER = os.environ.get('SUDO_USER', 'root')

def setup_directories(base_dir):
    # create fresh directories and clean old ones
    os.system(f"rm -fr {base_dir}")
    nodes = ["auth", "entry", "middle", "exit", "client"]
    for node in nodes:
        path = base_dir / node / "keys"
        path.mkdir(parents=True, exist_ok=True)
    os.system(f"chown -R {SUDO_USER}:{SUDO_USER} {base_dir}")

def generate_authority_keys(base_dir, auth_ip):
    # generate ID keys and certs for the directory authority
    auth_dir = base_dir / "auth"
    keys_dir = auth_dir / "keys"

    info("\n[info] Generating directory authority keys...\n")
    # use tor-gencert to do that
    cmd = (
        f"sudo -u {SUDO_USER} tor-gencert --create-identity-key "
        f"-m 12 -a {auth_ip}:7000 "
        f"-i {keys_dir}/authority_identity_key "
        f"-s {keys_dir}/authority_signing_key "
        f"-c {keys_dir}/authority_certificate "
        f"--passphrase-fd 0 < /dev/null"
    )
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        info(f"[error] tor-gencert failed:\n{result.stderr}\n")

    # get generated fingerprint from the certificate
    # the 'fingerprint' line in authority_certificate holds the v3 identity fingerprint
    fingerprint = ""
    with open(keys_dir / "authority_certificate", "r") as f:
        for line in f:
            if line.lower().startswith("fingerprint"):
                fingerprint = line.split()[1].strip()
                break
    return fingerprint

def write_torrc(node_type, path, ip, auth_ip, auth_fingerprint, target_server_ip=""):
    # dynamically generate torrc for a specific node type.
    #
    # common settings for all nodes:
    #   TestingTorNetwork 1  - enables fast-bootstrap testing mode
    #   AssumeReachable 1    - skips self-reachability checks
    #   RunAsDaemon 1        - fork to background (listed once, here)
    torrc_content = f"""TestingTorNetwork 1
DataDirectory {path}
Log notice file {path}/notice.log
AssumeReachable 1
RunAsDaemon 1
ControlPort 9051
"""

    # FIX: the DirAuthority line is required in EVERY node's torrc, including
    # the authority itself. Without it the authority doesn't know its own
    # v3ident, exits before writing its log, and all other nodes get
    # "Connection refused" on port 5000.
    dir_authority_line = (
        f"DirAuthority auth orport=5000 no-v2 "
        f"v3ident={auth_fingerprint} {auth_ip}:7000 {auth_fingerprint}\n"
    )

    if node_type == "auth":
        torrc_content += f"""Nickname DirAuthority
Address {ip}
ORPort 5000
DirPort 7000
AuthoritativeDirectory 1
V3AuthoritativeDirectory 1
{dir_authority_line}
TestingV3AuthInitialVotingInterval 20
TestingV3AuthInitialVoteDelay 4
TestingV3AuthInitialDistDelay 4
TestingMinExitFlagThreshold 0
TestingDirAuthVoteExit *
TestingDirAuthVoteGuard *
TestingAuthDirTimeToLearnReachability 0
ExitPolicy reject *:*
"""

    elif node_type == "relay":
        torrc_content += f"""Nickname RelayNode
Address {ip}
ORPort 5000
DirPort 7000
{dir_authority_line}
ExitPolicy reject *:*
"""

    elif node_type == "exit":
        # FIX: was "NickName" (wrong case for the middle N, harmless but wrong)
        torrc_content += f"""Nickname ExitNode
Address {ip}
ORPort 5000
DirPort 7000
{dir_authority_line}
ExitRelay 1
AllowSingleHopExits 1
ExitPolicy accept *:*
"""

    elif node_type == "client":
        torrc_content += f"""Nickname TorClient
{dir_authority_line}
SocksPort {ip}:9050
# FIX: with only 3 relays the client needs a lower threshold to build circuits
PathsNeededToBuildCircuits 0.25
"""

    with open(path / "torrc", "w") as f:
        f.write(torrc_content)
    os.system(f"chown {SUDO_USER}:{SUDO_USER} {path}/torrc")

def wait_for_bootstrap(log_path, label, timeout=120):
    """Poll a tor notice.log until we see 'Bootstrapped 100%' or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with open(log_path, "r") as f:
                for line in f:
                    if "Bootstrapped 100%" in line:
                        info(f"[info] {label} fully bootstrapped.\n")
                        return True
        except FileNotFoundError:
            pass
        time.sleep(2)
    info(f"[warn] {label} did not reach 100% bootstrap within {timeout}s.\n")
    return False

def create_network():
    setLogLevel("info")
    base_dir = Path("/tmp/tor_lab")

    info("[info] Creating Tor data directories...\n")
    setup_directories(base_dir)

    net = Mininet(controller=OVSController, autoSetMacs=True)
    net.addController('c0')

    info("[info] Adding virtual hosts...\n")
    client  = net.addHost('client',   ip='10.0.0.1/24')
    auth    = net.addHost('auth',     ip='10.0.0.2/24')
    entry   = net.addHost('entry',    ip='10.0.0.3/24')
    middle  = net.addHost('middle',   ip='10.0.0.4/24')
    exitnode = net.addHost('exitnode', ip='10.0.0.5/24')
    server  = net.addHost('server',   ip='10.0.0.6/24')

    switch = net.addSwitch('s1')

    for h in [client, auth, entry, middle, exitnode, server]:
        net.addLink(h, switch)

    net.start()

    # generate authority cert+keys before writing torrc files, since the
    # fingerprint is embedded in every node's DirAuthority line
    auth_fp = generate_authority_keys(base_dir, "10.0.0.2")
    if not auth_fp:
        info("[error] Could not extract authority fingerprint — aborting.\n")
        net.stop()
        return
    info(f"[info] Authority fingerprint: {auth_fp}\n")

    write_torrc("auth",   base_dir / "auth",   "10.0.0.2", "10.0.0.2", auth_fp)
    write_torrc("relay",  base_dir / "entry",  "10.0.0.3", "10.0.0.2", auth_fp)
    write_torrc("relay",  base_dir / "middle", "10.0.0.4", "10.0.0.2", auth_fp)
    write_torrc("exit",   base_dir / "exit",   "10.0.0.5", "10.0.0.2", auth_fp)
    write_torrc("client", base_dir / "client", "10.0.0.1", "10.0.0.2", auth_fp)

    # start target webserver
    info("[info] Starting webserver on 10.0.0.6:8080...\n")
    server.cmd("mkdir -p /tmp/fake_site")
    server.cmd("echo '<html><body><h1>Success! Traffic routed through Tor!</h1></body></html>' > /tmp/fake_site/index.html")
    server.cmd("python3 -m http.server 8080 --directory /tmp/fake_site &")

    info("[info] Starting directory authority...\n")
    auth.cmd(f"sudo -u {SUDO_USER} tor -f {base_dir}/auth/torrc &")

    # give auth a moment to bind its ports before relays try to connect
    time.sleep(5)

    info("[info] Starting relays...\n")
    entry.cmd(f"sudo -u {SUDO_USER} tor -f {base_dir}/entry/torrc &")
    middle.cmd(f"sudo -u {SUDO_USER} tor -f {base_dir}/middle/torrc &")
    exitnode.cmd(f"sudo -u {SUDO_USER} tor -f {base_dir}/exit/torrc &")

    info("\n[info] Waiting for authority to bootstrap...\n")
    wait_for_bootstrap(base_dir / "auth" / "notice.log", "authority", timeout=60)

    info("[info] Waiting for relays to bootstrap (building consensus)...\n")
    for label, log in [("entry", "entry"), ("middle", "middle"), ("exit", "exit")]:
        wait_for_bootstrap(base_dir / label / "notice.log", label, timeout=120)

    info("[info] Starting Tor client...\n")
    client.cmd(f"sudo -u {SUDO_USER} tor -f {base_dir}/client/torrc &")

    info("[info] Waiting for client to bootstrap...\n")
    wait_for_bootstrap(base_dir / "client" / "notice.log", "client", timeout=120)

    info("\n" + "="*50 + "\n")
    info("MINIMAL PRIVATE TOR NETWORK READY\n")
    info("To test the network, run this in the mininet CLI:\n")
    info("  client curl --socks5-hostname 10.0.0.1:9050 http://10.0.0.6:8080\n")
    info("="*50 + "\n")

    CLI(net)

    info("[info] Shutting down Tor processes...\n")
    for host in [auth, entry, middle, exitnode, client]:
        host.cmd("killall tor")
    server.cmd("killall python3")
    net.stop()

if __name__ == '__main__':
    create_network()
