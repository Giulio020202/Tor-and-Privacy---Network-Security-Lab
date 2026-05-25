import pandas as pd
import streamlit as st
import hashlib
import random
import time
import ipaddress

# apply sha256 hash function
def sha256_hash(value):
    return hashlib.sha256(str(value).encode()).hexdigest()

# show the DNS dataset
def step_0():
    st.write(
        """
        # Step 0: Dataset Analysis
        The dataset is an official Wireshark Sample Capture containing various
        DNS lookups
        """
    )
    st.dataframe(st.session_state.df)
    
    st.subheader("Step 0.0: Wireshark Analysis")
    st.write(
        """
        Analyze the file dns.cap with Wireshark (command wireshark dns.cap)
        """
    )

    st.subheader("Next Step")
    st.write(
        """
        Press the button to go to the next step
        """
    )
    if st.button("Next step"):
        st.session_state.step = 1
        st.rerun()

# apply hash and perform brute-force attack 
def step_1():
    st.write(
        """
        # Step 1: Pseudonymization Technique - Hashing Function
        """
    )

    st.subheader("Step 1.1: Apply SHA256")
    st.write(
        """
        Press the button to apply SHA256 to the source and destination IP
        addresses.
        """
    )
    if st.button("SHA256"):
        st.session_state.df["IP_SRC"] = st.session_state.df["IP_SRC"].apply(
            sha256_hash
        )
        st.session_state.df["IP_DST"] = st.session_state.df["IP_DST"].apply(
            sha256_hash
        )
        st.session_state.hashed = True

    st.dataframe(st.session_state.df)

    st.subheader("Step 1.2: Brute-force Attack")
    st.write(
        """
        Choice IP range and press the button to perform a brute-force
        attack.
        """
    )
    st.write("Original IPs:\n")
    for ip in original_ips:
        st.write(f"- {ip}\n")

    attack_method = st.selectbox(
        "Choose the IP range (default 192.168.170.x and 217.13.4.x)",
        [
            "192.168.170.x and 217.13.4.x",
            "192.168.x.x and 217.13.x.x",
            "192.x.x.x and 217.x.x.x"
        ]
    )

    if st.button("Brute-force attack"):
        hashed_ips = pd.unique(
            st.session_state.df[['IP_SRC', 'IP_DST']].values.ravel()
        )

        find = 0
        recovered = {}
        start = time.time()

        st.write("Starting the attack...\n\n")
        st.write("Recovered IPs:\n")
        match attack_method:
            case "192.168.x.x and 217.13.x.x":
                net1 = ipaddress.ip_network("192.168.0.0/16")
                net2 = ipaddress.ip_network("217.13.0.0/16")
            case "192.x.x.x and 217.x.x.x":
                net1 = ipaddress.ip_network("192.0.0.0/8")
                net2 = ipaddress.ip_network("217.0.0.0/8")
            case _:
                net1 = ipaddress.ip_network("192.168.170.0/24")
                net2 = ipaddress.ip_network("217.13.4.0/24")
        

        for ip in net1.hosts():
            h = hashlib.sha256(str(ip).encode()).hexdigest()

            if h in hashed_ips:
                recovered[h] = str(ip)
                find += 1
                st.write(f"{h} -> {ip}\n")

                if find == len(hashed_ips) - 1:
                    break

        for ip in net2.hosts():
            h = hashlib.sha256(str(ip).encode()).hexdigest()

            if h in hashed_ips:
                recovered[h] = str(ip)
                find += 1
                st.write(f"{h} -> {ip}\n")

                if find == len(hashed_ips):
                    break

        end = time.time()

        st.write(f"\nExecution time: {end - start} seconds")

        if len(recovered)==0:
            st.write("\n\nWARNING: You did not apply SHA256, attack failed!")

    st.subheader("Next Step")
    st.write(
        """
        Press the button to go to the next step
        """
    )
    if st.button("Next step"):
        st.session_state.step = 2
        st.rerun()

# apply RNG
def step_2():
    st.write(
        """
        # Step 2: Pseudonymization Technique - RNG
        """
    )
    st.subheader("Step 2.1")
    st.write(
        """
        Press the button to apply RNG technique to the source and destination IP
        addresses.
        """
    )
    if st.button("RNG"):
        unique_ips = pd.unique(packets[['IP_SRC', 'IP_DST']].values.ravel())
        pseudonyms = {ip: random.randint(1, 255) for ip in unique_ips}
        packets['IP_SRC'] = packets['IP_SRC'].map(pseudonyms)
        packets['IP_DST'] = packets['IP_DST'].map(pseudonyms)
        st.session_state.df = packets

    st.dataframe(st.session_state.df)

    st.subheader("Next Step")
    st.write(
        """
        Press the button to go to the next step
        """
    )
    if st.button("Next step"):
        st.session_state.step = 3
        st.rerun()

# apply RNG per packet
def step_3():
    st.write(
        """
        # Step 3: Pseudonymization Technique - RNG per Packet
        """
    )
    st.subheader("Step 2.1")
    st.write(
        """
        Press the button to apply RNG per packet technique to the source and
        destination IP addresses.
        """
    )
    if st.button("RNG per packet"):
        packets['IP_SRC'] = [
            random.randint(1, 255) for _ in range(len(packets))
        ]
        packets['IP_DST'] = [
            random.randint(1, 255) for _ in range(len(packets))
        ]
        st.session_state.df = packets

    st.dataframe(st.session_state.df)

packets = pd.read_csv("dns_new.csv")
original_ips = pd.unique(packets[['IP_SRC', 'IP_DST']].values.ravel())
# reset the session dataframe to packets for every step excepted for hash one
if "step" not in st.session_state or st.session_state.step != 1:
    st.session_state.df = packets

# based on the step execute the page
if "step" not in st.session_state:
    st.session_state.step = 0
if st.session_state.step == 0:
    step_0()    # analyze dataset
elif st.session_state.step == 1:
    step_1()    # hash and brute-force attack
elif st.session_state.step == 2:
    step_2()    # RNG
elif st.session_state.step == 3:
    step_3()    # RNG per packet
