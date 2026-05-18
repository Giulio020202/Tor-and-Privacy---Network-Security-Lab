# Tor and Privacy - Network Security Lab
Repository for our lecture about Tor and Privacy for the Network Security 2026 course at Università di Trento.
It is divided in 3 parts: A barebone simulation of a onion network, a demo of a timing based deanonymization attack on said network and a deanonymization attack on a pseudoanonymized dataset.

## Onion Network

`onion-net/topology.py` contains a barebone implementation of an onion network implemented in python using mininet. The layout consists of a client connected to a server through onion-like relays, all of wich are directly connected to their neighbours (i.e. no switches).
The network also implements artificial delays so that the timing attack can be mounted.

### Run

The mininet network can be started with:

```bash
sudo python3 onion-net/topology.py
```
This will open mininet CLI where each node can be manually contolled.

To auto-capture pcap files trough tcpdump for every path interface, run:

```bash
sudo python3 onion-net/topology.py --capture
```

To start a mock HTTP web request from the client to the server, run:

```bash
sudo python3 onion-net/topology.py --http-demo
```

To measure per-hop and end-to-end latency through the relay path, run:

```bash
sudo python3 onion-net/topology.py --test-latency
```
```

### Capture traffic

Use Wireshark or tcpdump on the Mininet interfaces, for example:

```bash
sudo wireshark -k -i entry-eth0
```

- `-i` selects the interface to capture from
- `-k` starts capture immediately on launch


To remove all generated captures:

```bash
sudo make clean
```

Inside the Mininet CLI you can also test connectivity with:

```bash
pingall
```