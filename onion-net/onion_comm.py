import argparse
import socket
import sys
import urllib.request

from onion_proto import DEFAULT_ROUTE, HOP_KEYS, build_onion_packet, decrypt_layer, entry_address, unpack_layer



def recvall(conn):
    data = bytearray()
    while True:
        chunk = conn.recv(4096)
        if not chunk:
            break
        data.extend(chunk)
    return bytes(data)


def debug_print(message: str) -> None:
    print(message)
    sys.stdout.flush()


def send_packet(address: str, packet: bytes) -> None:
    host, port = address.split(":")
    port = int(port)
    with socket.create_connection((host, port), timeout=10) as sock:
        sock.sendall(packet)


def perform_http_request(server_ip: str, server_port: int, path: str) -> str:
    url = f"http://{server_ip}:{server_port}{path}"
    with urllib.request.urlopen(url, timeout=10) as response:
        return response.read().decode("utf-8", errors="replace")


def run_relay(key_name: str, listen_ip: str, listen_port: int, server_ip: str, server_port: int) -> None:
    if key_name not in HOP_KEYS:
        raise ValueError(f"Unknown relay key: {key_name}")

    debug_print(f"[{key_name}] listening on {listen_ip}:{listen_port}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((listen_ip, listen_port))
        listener.listen(1)
        conn, _ = listener.accept()
        debug_print(f"[{key_name}] accepted connection")
        with conn:
            encrypted_data = recvall(conn)

    debug_print(f"[{key_name}] received {len(encrypted_data)} bytes")
    layer = decrypt_layer(encrypted_data, key_name)
    message = unpack_layer(layer)
    next_hop = message["next"]
    payload = message["payload"]
    debug_print(f"[{key_name}] decrypted layer; next hop={next_hop}")

    if next_hop == "server":
        path = payload.decode("utf-8")
        debug_print(f"[{key_name}] exit relay performing HTTP GET {path}")
        response = perform_http_request(server_ip, server_port, path)
        debug_print(f"[{key_name}] exit relay fetched {len(response)} bytes")
        print("EXIT node received request and fetched server response:")
        print(response[:512])
        sys.stdout.flush()
    else:
        debug_print(f"[{key_name}] forwarding payload to {next_hop}")
        send_packet(next_hop, payload)


def run_client(entry_ip: str, entry_port: int, path: str = "/") -> None:
    address = f"{entry_ip}:{entry_port}"
    onion_packet = build_onion_packet(path)
    debug_print(f"[client] building onion request for path {path}")
    send_packet(address, onion_packet)
    print(f"CLIENT sent onion request to {address}")
    sys.stdout.flush()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Minimal mock onion relay client/relay")
    parser.add_argument("--mode", choices=["client", "relay"], required=True)
    parser.add_argument("--key", choices=list(HOP_KEYS), help="relay key name")
    parser.add_argument("--listen-ip", help="relay listen IP")
    parser.add_argument("--listen-port", type=int, help="relay listen port")
    parser.add_argument("--server-ip", default="10.0.0.7", help="HTTP server IP for exit node")
    parser.add_argument("--server-port", type=int, default=8080, help="HTTP server port for exit node")
    parser.add_argument("--entry-ip", default="10.0.0.1", help="entry relay IP for client mode")
    parser.add_argument("--entry-port", type=int, default=9001, help="entry relay port for client mode")
    parser.add_argument("--path", default="/", help="HTTP path to request")
    args = parser.parse_args()

    if args.mode == "client":
        run_client(args.entry_ip, args.entry_port, args.path)
    else:
        run_relay(args.key, args.listen_ip, args.listen_port, args.server_ip, args.server_port)
