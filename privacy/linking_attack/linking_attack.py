import pandas as pd
import sys
import os
from tabulate import tabulate

if len(sys.argv) > 2:
    raise Exception("arguments must be less than two")

# if the .csv file is inserted, check its existence
if len(sys.argv) == 2:        
    p_path = sys.argv[1]
else:
    p_path = "patients.csv"     # default patients dataset

if not os.path.exists(p_path):
    raise Exception ("patients dataset does not exist")

if not os.path.exists("voters.csv"):
    raise Exception ("voters dataset does not exist")

patients = pd.read_csv(p_path, index_col=False)
voters = pd.read_csv("voters.csv", index_col=False)

patients = patients.add_prefix("P_")
voters = voters.add_prefix("V_")

# INNER JOIN ON QUASI_IDENTIFIERS
# TODO: find quasi-identifiers and insert them in the on argument, ex:
# left_on = ["P_NAME", "P_ID"]
# right_on = ["V_NAME", "V_ID"]
try:
    linked = pd.merge(
        patients,
        voters,
        left_on=["P_ZIP", "P_BIRTH_DATE", "P_SEX"],
        right_on=["V_ZIP", "V_BIRTH_DATE", "V_SEX"],
        how='inner'
    )
    print("MATCHES:")
    print(tabulate(linked, headers="keys", tablefmt="fancy_grid", showindex=False))
    print("\nTOT MATCHES:", len(linked))
except KeyError:
    print("You inserted the wrong quasi-identifiers")