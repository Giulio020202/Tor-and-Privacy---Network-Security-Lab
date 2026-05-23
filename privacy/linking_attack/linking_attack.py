import pandas as pd
import sys
import os

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

patients = pd.read_csv(p_path, index_col=0)
voters = pd.read_csv("voters.csv", index_col=0)

# INNER JOIN ON QUASI_IDENTIFIERS
# TODO: find quasi-identifiers and insert them in the on argument, ex:
# on = ["NAME", "ID"]
try:
    linked = pd.merge(
        patients,
        voters,
        on=["ZIP", "BIRTH_DATE", "SEX"],
        how='inner'
    )
    print("MATCHES:")
    print(linked)
    print("\nTOT MATCHES:", len(linked))
except KeyError:
    print("You inserted the wrong quasi-identifiers")