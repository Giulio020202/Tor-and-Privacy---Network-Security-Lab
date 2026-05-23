import argparse
import math
from pathlib import Path
from scapy.all import PcapReader, ICMP

def get_packet_times(filename):
    # Extract absolute timestamps from a pcap file
    times = []
    try:
        with PcapReader(str(filename)) as pcap:
            for pkt in pcap:
                if pkt.haslayer(ICMP) and pkt[ICMP].type == 8:
                    times.append(float(pkt.time))
    except FileNotFoundError:
        print(f"[!] Could not find {filename}. Did you run the topology with --capture?")
        exit(1)
    return times

def create_bins(times, global_start, global_end, bin_size=0.5):
    # turn list of timestamps into a vector of packet counts per time bin.
    num_bins = math.ceil((global_end - global_start) / bin_size)
    bins = [0] * num_bins

    for t in times:
        idx = int((t - global_start) / bin_size)
        if 0 <= idx < num_bins:
            bins[idx] += 1
    return bins

def pearson_correlation(x, y):
    # calculate the Pearson correlation coefficient between two lists.
    if len(x) != len(y) or len(x) == 0:
        return 0.0

    n = len(x)
    mean_x = sum(x) / n
    mean_y = sum(y) / n

    numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    den_x = sum((x[i] - mean_x) ** 2 for i in range(n))
    den_y = sum((y[i] - mean_y) ** 2 for i in range(n))

    if den_x == 0 or den_y == 0:
        return 0.0

    return numerator / math.sqrt(den_x * den_y)

def main():
    parser = argparse.ArgumentParser(description="Timing Correlation Attack Simulator")
    parser.add_argument("--dir", default="captures", help="Directory containing the pcap files")
    parser.add_argument("--bin-size", type=float, default=0.5, help="Size of the time bins in (float) seconds")
    args = parser.parse_args()

    capture_dir = Path(args.dir)

    # define the points the attacker controls

    # ingress: traffic entering the onion network through the entry node
    ingress_files = {
        "Client 1 Stream": capture_dir / "entry-from-c1.pcap",
        "Client 2 Stream": capture_dir / "entry-from-c2.pcap"
    }
    # egress: traffic leaving the onio network through exit node
    egress_files = {
        "Server 1 Stream": capture_dir / "exitnode-to-s1.pcap",
        "Server 2 Stream": capture_dir / "exitnode-to-s2.pcap"
    }

    print("[*] Extracting packet timestamps from captures...")

    ingress_data = {name: get_packet_times(f) for name, f in ingress_files.items()}
    egress_data = {name: get_packet_times(f) for name, f in egress_files.items()}

    # sync timelines, to compare bins the must start at same absolute time
    all_times = [t for times in ingress_data.values() for t in times] + \
        [t for times in egress_data.values() for t in times]

    if not all_times:
        print("[!] No packets found. Ensure the simulation ran traffic.")
        return

    global_start = min(all_times)
    global_end = max(all_times)

    print(f"[*] Total capture duration: {global_end - global_start:.2f} seconds")
    print(f"[*] Binning traffic into {args.bin_size}-second windows...")

    ingress_bins = {name: create_bins(times, global_start, global_end, args.bin_size) for name, times in ingress_data.items()}
    egress_bins = {name: create_bins(times, global_start, global_end, args.bin_size) for name, times in egress_data.items()}

    print("\n")
    print("TIMING CORRELATION RESULTS")
    print("\n")

    for in_name, in_vector in ingress_bins.items():
        print(f"Analyzing: {in_name}")
        best_match = None
        highest_corr = -1.0

        for eg_name, eg_vector in egress_bins.items():
            # Shift the egress vector slightly backwards to account for network latency
            # (The exit packets arrive slightly later than the entry packets)
            # in a real attack we would test multiple offsets. Here we just correlate
            corr = pearson_correlation(in_vector, eg_vector)
            print(f"  -> Correlation with {eg_name}: {corr:.4f}")

            if corr > highest_corr:
                highest_corr = corr
                best_match = eg_name

        print(f"  [!] CONCLUSION: {in_name} is highly likely communicating with {best_match.replace('Stream', '')}")

if __name__ == "__main__":
    main()
    
