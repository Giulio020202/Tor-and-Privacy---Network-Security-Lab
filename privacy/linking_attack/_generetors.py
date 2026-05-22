import random 

class PatientGenerator():
    """Generates patients.

    Generate entries for the patients dataset.

    Attributes:
        g: Mimesis Generic object that generates patients' birth date and sex.
        id: sequential counter (pseudonymization technique for patients' name)
        diagnoses: list of possible diagnoses.
    """
    def __init__(self, g, id = 0):
        """Method to initialize class attributes.

        Args:
            g: Mimesis Generic object.
        """
        self.g = g

        self.id = id
        self.diagnoses = [
            "Hypertension", "Diabetes", "Stroke", "Osteoporosis", "Arthritis",
            "Tuberculosis", "Gastritis", "Pneumonia", "Bronchitis"
        ]

    def generate_patient(self, zip, birth_date, sex, diagnosis):
        """Method to generate a specific patient.

        Args:
            zip: zip of the patient.
            birth_date: birth date of the patient.
            sex: sex of the patient.
            diagnosis: diagnosis of the patient.

        Returns:
            dictionary containing the patient's information.
        """
        self.id+=1
        return {
            "ID": self.id,
            "ZIP": zip,
            "BIRTH_DATE": birth_date,
            "SEX": sex,
            "DIAGNOSIS": diagnosis
        }
    
    def generate_k_patient(self, zip, birth_date, sex, original_diagnosis):
        """Method to generate a patient for k-anonymity.

        Args:
            zip: zip of the patient.
            birth_date: birth date of the patient.
            sex: sex of the patient.
            original_diagnosis: real diagnosis of the patient.

        Returns:
            a "false" entry of the original patient
        """  
        new_diagnosis = random.choice(self.diagnoses)
        if new_diagnosis == original_diagnosis:
            new_diagnosis = self.diagnoses[0]
        self.id+=1
        return {
            "ID": self.id,
            "ZIP": zip,
            "BIRTH_DATE": birth_date,
            "SEX": sex,
            "DIAGNOSIS": new_diagnosis
        }

    def generate_random_patient(self):
        """Method to generate a random patient.

        Returns:
            dictionary containing the patient's information
        """
        self.id+=1
        # zip codes of Massachusetts
        zip = random.randrange(1001, 2791)
        # zip 2139 only for William Floyd Weld (the attack target)
        if zip == 2139: zip+=1

        return {
            "ID": self.id,
            "ZIP": f"0{zip}",
            "BIRTH_DATE": self.g.person.birthdate(1916, 1995),
            "SEX": self.g.person.sex(),
            "DIAGNOSIS": random.choice(self.diagnoses)
        }

class VoterGenerator():
    """Generates voters.

    Generate entries for the voters dataset.

    Attributes:
        g: Mimesis Generic object that generates patients' birth date and sex.
        affiliations: list of possible political affiliations.
        zips: zips list of Cambridge, Massachusetts.
    """
    def __init__(self, g):
        """Method to initialize class attributes.

        Args:
            g: Mimesis Generic object.
        """
        self.g = g

        self.party_affiliations = [
            "Democratic", "Republican", "Unenrolled", "Libertarian"
        ]
        self.zips = ["02138", "02139", "02140", "02141", "02142"]

    def generate_random_voter(self):
        """Method to generate a random voter.

        Returns:
            dictionary containing the voter's information
        """
        return {
            "NAME": self.g.person.full_name(),
            "ZIP": random.choice(self.zips),
            "BIRTH_DATE": self.g.person.birthdate(1916, 1977),
            "SEX": self.g.person.sex(),
            "PARTY_AFF": random.choice(self.party_affiliations),
        }
    
    def generate_voter(self, birth_date, sex):
        """Method to generate a specific voter.

        Args:
            birth_date: birth date of the patient.
            sex: sex of the patient.

        Returns:
            dictionary containing the voter's information
        """
        zip = random.choice(self.zips)
        # zip 2139 only for William Floyd Weld (the attack target)
        if zip == "02139": zip = "02140"
    
        return {
            "NAME": self.g.person.full_name(),
            "ZIP": zip,
            "BIRTH_DATE": birth_date,
            "SEX": sex,
            "PARTY_AFF": random.choice(self.party_affiliations),
        }