import base64
import json

HOP_KEYS = {
    "entry": b"entry_key_123456",
    "middle": b"middle_key_234567",
    "exit": b"exit_key_345678",
}

# A fixed, minimal route for the mockup.
DEFAULT_ROUTE = [
    ("entry", "10.0.0.1", 9001),
    ("middle", "10.0.0.3", 9002),
    ("exit", "10.0.0.5", 9003),
]


def xor_bytes(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def encrypt_layer(data: bytes, key_name: str) -> bytes:
    return xor_bytes(data, HOP_KEYS[key_name])


def decrypt_layer(data: bytes, key_name: str) -> bytes:
    return xor_bytes(data, HOP_KEYS[key_name])


def pack_layer(next_hop: str, payload_bytes: bytes) -> bytes:
    layer = {
        "next": next_hop,
        "payload": base64.b64encode(payload_bytes).decode("ascii"),
    }
    return json.dumps(layer).encode("utf-8")


def unpack_layer(layer_bytes: bytes) -> dict:
    decoded = json.loads(layer_bytes.decode("utf-8"))
    decoded["payload"] = base64.b64decode(decoded["payload"].encode("ascii"))
    return decoded


def build_request_path(path: str = "/") -> bytes:
    return path.encode("utf-8")


def build_onion_packet(path: str = "/") -> bytes:
    payload = build_request_path(path)
    for index in reversed(range(len(DEFAULT_ROUTE))):
        hop_name, hop_ip, hop_port = DEFAULT_ROUTE[index]
        next_hop = "server" if hop_name == "exit" else f"{DEFAULT_ROUTE[index + 1][1]}:{DEFAULT_ROUTE[index + 1][2]}"
        layer = pack_layer(next_hop, payload)
        payload = encrypt_layer(layer, hop_name)
    return payload


def entry_address() -> str:
    first_hop = DEFAULT_ROUTE[0]
    return f"{first_hop[1]}:{first_hop[2]}"
