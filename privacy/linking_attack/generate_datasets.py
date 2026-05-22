from mimesis import Generic
from mimesis.locales import Locale
from _generetors import PatientGenerator, VoterGenerator
import csv
import sys

if len(sys.argv) > 2:
    raise Exception("arguments must be less than three")

# if the number fo entries is inserted, check its correctness
if len(sys.argv) == 2:
    if int(sys.argv[1]) < 8:
        raise Exception ("the number of entries must be bigger or equal to 8")
    
    num_records = int(sys.argv[1])
else:
    num_records = 1000   # default 1000 entries

g = Generic(locale = Locale.EN)

p_generator = PatientGenerator(g)
num_p_records = num_records - 1 # number of rand entries of the patients dataset
# generate target entry
target_p = p_generator.generate_patient("02139", "1945-07-31", "Male", "Stroke")
# generate random patients
patients = [p_generator.generate_random_patient() for _ in range(num_p_records)]
patients.insert(0, target_p)    # add the target to the patients

with open("patients.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=patients[0].keys())
    writer.writeheader()
    writer.writerows(patients)

v_generator = VoterGenerator(g)
num_v_records = num_records - 7 # number of rand entries of the voters dataset

# create targets' entries
targets_m = [v_generator.generate_voter("1945-07-31", "Male") for _ in range(2)]
targets_f = [
    v_generator.generate_voter("1945-07-31", "Female") for _ in range(3)
]
target_v = [{
    "NAME": "William Floyd Weld",
    "ZIP": "02139",
    "BIRTH_DATE": "1945-07-31",
    "SEX": "Male",
    "PARTY_AFF": "Republican"
}]
voters = [v_generator.generate_random_voter() for _ in range(num_v_records)]
voters = target_v + targets_m + targets_f + voters

with open("voters.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=voters[0].keys())
    writer.writeheader()
    writer.writerows(voters)