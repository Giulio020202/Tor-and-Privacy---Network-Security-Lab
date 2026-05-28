import argparse
import sys
import pandas as pd
from scapy.all import rdpcap
import warnings

warnings.filterwarnings("ignore")

def extract_packets(pcap_file, target_ports):
    """Read PCAP and extracts relevant TCP packets into a list of dictionaries."""
    print(f"info: Parsing {pcap_file}...")
    try:
        packets = rdpcap(pcap_file)
    except FileNotFoundError:
        print(f"error: file '{pcap_file}' not found.")
        sys.exit(1)

    if not packets:
        print(f"warning: {pcap_file} is empty.")
        return []

    data = []
    start_time = float(packets[0].time)

    for pkt in packets:
        if pkt.haslayer("TCP"):
            src_port = pkt["TCP"].sport
            dst_port = pkt["TCP"].dport

            if src_port in target_ports or dst_port in target_ports:
                # label data with port we're monitoring
                port = src_port if src_port in target_ports else dst_port
                rel_time = float(pkt.time) - start_time
                data.append({"Time": rel_time, "Port": port, "Bytes": len(pkt)})

    return data

def bin_traffic(packet_data, bin_size):
    """Converts raw packet data into time-binned DataFrames."""
    df = pd.DataFrame(packet_data)
    if df.empty:
        return pd.DataFrame()

    df["Time"] = pd.to_datetime(df["Time"], unit='s')

    binned = df.groupby([pd.Grouper(key="Time", freq=bin_size), "Port"])["Bytes"].sum().unstack(fill_value=0)

    binned = binned.resample(bin_size).asfreq().fillna(0)
    
    return binned

def main():
    parser = argparse.ArgumentParser(description="Tor Timing Correlation Analyzer")
    parser.add_argument("--ingress-file", default="ingress.pcap", help="Ingress PCAP file")
    parser.add_argument("--egress-file", default="egress.pcap", help="Egress PCAP file")
    parser.add_argument("--ingress-ports", type=int, nargs='+', default=[9005, 9006], help="Ingress ports to monitor")
    parser.add_argument("--egress-ports", type=int, nargs='+', default=[8080, 8081], help="Egress ports to monitor")
    parser.add_argument("--bin-size", default="500ms", help="Time bin size (e.g. '500ms', '1ms')")

    args = parser.parse_args()

    # extract raw packets
    ingress_data = extract_packets(args.ingress_file, args.ingress_ports)
    egress_data = extract_packets(args.egress_file, args.egress_ports)

    # convert to binned timelines
    ingress_bins = bin_traffic(ingress_data, args.bin_size)
    egress_bins = bin_traffic(egress_data, args.bin_size)

    # align timelines
    combined_df = ingress_bins.join(egress_bins, how="outer").fillna(0)

    print("\n--- Time-Series Data (first 5 bins) ---")
    print(combined_df.head(5))

    # calculate and display correlation
    print("\n" + "="*50)
    print("  TIMING CORRELATION MATRIX".center(50))
    print("="*50)

    corr_matrix = combined_df.corr(method="pearson")

    valid_ingress = [p for p in args.ingress_ports if p in corr_matrix.index]
    valid_egress = [p for p in args.egress_ports if p in corr_matrix.columns]

    if not valid_ingress or not valid_egress:
        print("info: Not enough data to build correlation matrix. Check your captures.")
    else:
        results = corr_matrix.loc[valid_ingress, valid_egress]
        print(results.round(4))
    print("="*50)

if __name__ == "__main__":
    main()
                
