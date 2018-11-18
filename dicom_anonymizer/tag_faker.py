from faker import Faker
from .utils import random_with_n_digits


class TagFaker:
    def __init__(self, faker=Faker()):
        self.faker = faker

    def patient_name(self, sex: str = None):
        f = self.faker
        if sex is 'M':
            return f'{f.last_name()}^{f.first_name_male()}'
        elif sex is 'F':
            return f'{f.last_name()}^{f.first_name_female()}'
        else:
            return f'{f.last_name()}^{f.first_name()}'

    def patient_id(self, existing_subjects: dict = {}):
        anonymized_id = str(random_with_n_digits(9))
        if existing_subjects:
            existing_ids = [
                subject.get('PatientID')
                for subject in existing_subjects.values()
            ]
            while anonymized_id in existing_ids:
                anonymized_id = str(random_with_n_digits(9))
        return anonymized_id
