import pandas as pd
import sys
from mimesis import Generic
from mimesis.locales import Locale

from _generetors import PatientGenerator

if len(sys.argv) > 2:
    raise Exception("arguments must be less than three")

# if k (k-anonymity) is inserted, check its correctness
if len(sys.argv) == 2:
    if int(sys.argv[1]) < 2:
        raise Exception ("the value k must be bigger or equal to 2")
    
    k = int(sys.argv[1])
else:
    k = 2   # default 2-anonymity

patients = pd.read_csv("patients.csv", index_col=None)
# find unique quasi-identifiers entries
unique_entries = patients[
    ~patients.duplicated(subset=['ZIP', 'BIRTH_DATE', 'SEX'], keep=False)
]

g = Generic(locale = Locale.EN)
p_g = PatientGenerator(g, id = len(patients))

# generate k additional rows to avoid unique quasi-identifiers
for e in unique_entries.itertuples():
    for i in range(k-1):
        patients.loc[len(patients)] = p_g.generate_k_patient(
            e.ZIP, e.BIRTH_DATE, e.SEX, e.DIAGNOSIS
        )

patients.to_csv("k_patients.csv", index=False)