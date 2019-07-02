from faker import Faker
from .utils import id_generator


class TagFaker:
    METHOD_BY_TAG = {"PatientID": "patient_id", "PatientName": "patient_name"}
    VALID_TAGS = ("PatientID", "PatientName")

    def __init__(self, faker=Faker()):
        self.faker = faker

    def patient_name(self, sex: str = None):
        f = self.faker
        if sex is "M":
            return f"{f.last_name()}^{f.first_name_male()}"
        elif sex is "F":
            return f"{f.last_name()}^{f.first_name_female()}"
        else:
            return f"{f.last_name()}^{f.first_name()}"

    def patient_id(self, existing_subjects: dict = {}):
        anonymized_id = id_generator()

        # Make sure the generated ID is really new
        if existing_subjects:
            existing_ids = [
                subject.get("PatientID") for subject in existing_subjects.values()
            ]
            # In case this ID is already taken, generate a new one
            while anonymized_id in existing_ids:
                anonymized_id = id_generator()

        return anonymized_id

    def fake(self, tag_name: str, **kwargs):
        method_name = self.METHOD_BY_TAG[tag_name]
        method = getattr(self, method_name)
        if method:
            return method(**kwargs)
        else:
            raise NotImplementedError(
                f"TagFaker doesn't recognize {tag_name}.\nPlease choose from the following: {self.VALID_TAGS}"
            )
