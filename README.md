<h1 align="center">Tor and Privacy - Network Security Lab</h1>

## Table of Contents

- [About the Project](#about-the-project)
- [Tor](#tor)
  - [Onion Network](#onion-network)
    - [Run](#run)
- [Privacy](#privacy)
  - [Requirements](#requirements)
  - [Linking Attack](#linking-attack)
    - [Folder Organization](#folder-organization)
    - [Datasets Generation](#datasets-generation)
    - [K-anonymity](#k-anonymity)
    - [Re-identification Attack](#re-identification-attack)

# About the Project
Repository for our lecture about Tor and Privacy for the Network Security 2026 course at Università di Trento.
It is divided in 3 parts: A barebone simulation of a onion network, a demo of a timing based deanonymization attack on said network and a deanonymization attack on a pseudoanonymized dataset.

# Tor

## Onion Network

`onion-net/topology.py` contains a barebone implementation of an onion network implemented in python using mininet. The layout consists of a client connected to a server through onion-like relays, all of wich are directly connected to their neighbours (i.e. no switches).
The network also implements artificial delays so that the timing attack can be mounted.

### Run

The mininet network can be started with:

```bash
sudo python3 onion-net/topology.py
```
This will open mininet CLI where each node can be manually contolled.

To auto-capture pcap files through tcpdump for every path interface, run:

```bash
sudo python3 onion-net/topology.py --capture
```

To merge all generated PCAPs into a single file for Wireshark analysis, run:

```bash
./onion-net/merge_pcaps.sh
```

Or use the Makefile target:

```bash
make merge-captures
```

The merged file is written to `onion-net/captures/all-captures.pcap`.

To start a mock HTTP web request from the client to the server, run:

```bash
sudo python3 onion-net/topology.py --http-demo
```

To exercise a minimal layered onion request through entry/middle/exit, run:

```bash
sudo python3 onion-net/topology.py --onion-demo
```

The onion demo now prints per-node debug progress in the terminal so you can see request forwarding and response handling.

The onion demo code lives in `onion-net/onion_proto.py` and `onion-net/onion_comm.py`.

To measure per-hop and end-to-end latency through the relay path, run:

```bash
sudo python3 onion-net/topology.py --test-latency
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
# Privacy

## Requirements 
The attacks require the following Python modules:
- mimesis
- numpy 
- pandas

## Linking Attack

### Folder Organization
The `privacy/linking attack` directory contains the Latanya Sweeney
re-identification attack. It contains the following Python scripts:
- `_generators.py`: contains the PatientGenerator and VoterGenerator classes
used to create the entries of the patients and voters datasets
- `generate_datasets.py`: script that generates the datasets of the patients and
the voters
- `k_anonymity.py`: apply k-anonymity to the dataset of the patients
- `linking_attack.py`: performs the re-identification attack

### Datasets Generation
To generate the patients and voters datasets you need to run:

```bash
python3 generate_datasets.py <n_entry> 
```

n_entry is not necessary, it indicates the number of entries in the dataset
(the default is 1000). The script generates two datasets named
`patients.csv` and `voters.csv`.

### K-anonymity 
To apply k-anonymity to the patients dataset (`patients.csv`) you need to run:

```bash
python3 k_anonymity.py <k> 
```

k is not necessary, it indicates the level of k-anonymity (the default is 2). It
generates the dataset `k_patients.csv`.

### Re-identification Attack
To perform the linking attack you need to run:

```bash
python3 linking_attack.py <p_dataset> 
```

p_dataset is not necessary, it indicates the patients dataset (the default is 
`patients.csv`). 