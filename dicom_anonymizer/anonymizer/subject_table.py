import pandas as pd

from dicom_anonymizer.anonymizer.information_table import InformationTable
from dicom_anonymizer.dicom_handler import DicomHandler


class SubjectTable(InformationTable):
    COLUMNS = pd.MultiIndex.from_arrays([
        ["Anonymized"] * 3 + ["Raw"] * 11,
        ["Patient ID", "First Name", "Last Name"] * 2 + [
            "Sex",
            "Height",
            "Weight",
            "Birth Date",
            "Dominant Hand",
            "Email",
            "Phone Number",
            "Address",
        ],
    ])
    SHEET_NAME = 'Subjects'
    ID_INDEX = "Raw", "Patient ID"
    HEADER_COLUMNS = [0, 1]

    def generate_anonymized_information(self, sex: str = None) -> dict:
        fake_name = self.faker.patient_name(sex)
        last_name, first_name = fake_name.split("^")
        return {
            "Patient ID": self.faker.patient_id(),
            "First Name": first_name,
            "Last Name": last_name,
        }

    def create_series_from_dicom(self,
                                 dicom_handler: DicomHandler) -> pd.Series:
        raw = dicom_handler.subject_information
        anonymized = self.generate_anonymized_information(
            dicom_handler.patient_sex)
        raw = {("Raw", key): value for key, value in raw.items()}
        anonymized = {("Anonymized", key): value
                      for key, value in anonymized.items()}
        raw.update(anonymized)
        return pd.Series(raw)

    def add_from_dicom(self, dicom_handler: DicomHandler,
                       save: bool = True) -> None:
        subject_series = self.create_series_from_dicom(dicom_handler)
        self.add(subject_series, save=save)
        return subject_series

    def get_or_create_from_dicom(self, dicom_handler: DicomHandler):
        series = self.get(dicom_handler.subject_id)
        if series.empty:
            return self.add_from_dicom(dicom_handler)
        return series
