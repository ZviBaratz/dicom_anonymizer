import os
import pickle
import pydicom

from pydicom.dataset import FileDataset
from .tag_faker import TagFaker

PATIENT_ID_TAG = "PatientID"
VALID_TAGS = [PATIENT_ID_TAG, "PatientName"]


class Anonymizer:
    def __init__(self, associations_file: str = None):
        self.existing_subjects = self.load_associations(associations_file)
        self.faker = TagFaker()

    def update_existing_subjects(self, patient_id: str, **kwargs):
        if patient_id not in self.existing_subjects:
            self.existing_subjects[patient_id] = dict()
        self.existing_subjects[patient_id].update(kwargs)
        return self.existing_subjects

    def get_anonymized_value(self, dcm: FileDataset, tag_name: str):
        try:
            return self.existing_subjects[dcm.PatientID][tag_name]
        except KeyError:
            if tag_name is PATIENT_ID_TAG:
                new_value = self.faker.patient_id(self.existing_subjects)
            elif tag_name is "PatientName":
                new_value = self.faker.patient_name(dcm.PatientSex)
            else:
                raise NotImplementedError(
                    f"Invalid DICOM tag name! Expected a value from:\n{VALID_TAGS}\nGot: {tag_name}"
                )
            self.update_existing_subjects(dcm.PatientID, **{tag_name: new_value})
            return self.get_anonymized_value(dcm, tag_name)

    def anonymize_dcm_dataset(
        self, dcm: FileDataset, tag_names: list = VALID_TAGS
    ) -> FileDataset:
        not_patient_id = [tag for tag in tag_names if tag is not PATIENT_ID_TAG]
        for tag_name in not_patient_id:
            anonymized_value = self.get_anonymized_value(dcm, tag_name)
            setattr(dcm, tag_name, anonymized_value)
        anonymized_id = self.get_anonymized_value(dcm, PATIENT_ID_TAG)
        dcm.PatientID = anonymized_id
        return dcm

    def create_dcm_path(self, dcm: FileDataset, dest: str) -> str:
        return os.path.join(
            dest, dcm.PatientID, dcm.SeriesInstanceUID, f"{dcm.InstanceNumber}.dcm"
        )

    def save_dcm(self, dcm: FileDataset, path: str) -> bool:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            dcm.save_as(path)
            return True
        except Exception:
            print(f"Failed to save DICOM datast to {path}!")
            return False

    def read_dcm(self, path: str):
        try:
            return pydicom.dcmread(path)
        except Exception as e:
            print(f"Failed to read DICOM file from {path}!")
            print(e)

    def anonymize_dcm(self, source: str, dest: str):
        dcm = self.read_dcm(source)
        if isinstance(dcm, FileDataset):
            dcm = self.anonymize_dcm_dataset(dcm)
            path = self.create_dcm_path(dcm, dest)
            return self.save_dcm(dcm, path)

    def anonymize_tree(self, path: str, dest: str):
        for subdir, dirs, files in os.walk(path):
            for f in files:
                if f.endswith(".dcm"):
                    path = os.path.join(subdir, f)
                    self.anonymize_dcm(path, dest)

    def serialize_associations(self, path: str) -> bool:
        with open(path, "wb") as key_file:
            pickle.dump(self.existing_subjects, key_file)
            return True

    def load_associations(self, path: str) -> dict:
        if path and os.path.isfile(path):
            with open(path, "rb") as key_file:
                return pickle.load(key_file)
        return dict()
