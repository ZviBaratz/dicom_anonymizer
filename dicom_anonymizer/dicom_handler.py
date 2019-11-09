import os
import pandas as pd
import pydicom

from dicom_anonymizer.utils import format_date, format_time
from pathlib import Path


class DicomHandler:
    def __init__(self, path):
        self.path = str(path)
        self.dcm = self.read()

    def read(self) -> pydicom.FileDataset:
        try:
            return pydicom.read_file(self.path)
        except pydicom.filereader.InvalidDicomError:
            print(f"Failed to read {self.path}! Skipping...")

    def anonymized_name_from_series(self, series: pd.Series) -> str:
        first_name = series["Anonymized"]["First Name"]
        last_name = series["Anonymized"]["Last Name"]
        return f"{last_name}^{first_name}"

    def anonymize_by_series(self, series: pd.Series) -> None:
        self.dcm.PatientID = series["Anonymized"]["Patient ID"]
        self.dcm.PatientName = self.anonymized_name_from_series(series)

    def create_destination(self, base_directory: Path) -> Path:
        directory = base_directory / self.subject_id / self.scan_id
        directory.mkdir(parents=True, exist_ok=True)
        return directory / f"{self.instance_number}.dcm"

    def save(self, base_directory: Path) -> None:
        destination = self.create_destination(base_directory)
        if destination.is_file():
            relative = str(destination)[len(str(base_directory)):]
            print(f'{relative} exists! skipping...')
        else:
            self.dcm.save_as(str(destination))

    @property
    def subject_id(self) -> str:
        return self.dcm.PatientID

    @property
    def patient_sex(self) -> str:
        return self.dcm.PatientSex

    @property
    def scan_id(self) -> str:
        return self.dcm.SeriesInstanceUID

    @property
    def instance_number(self) -> int:
        return self.dcm.InstanceNumber

    @property
    def subject_information(self) -> dict:
        return {
            "Patient ID": self.dcm.PatientID,
            "First Name": self.dcm.PatientName.given_name,
            "Last Name": self.dcm.PatientName.family_name,
            "Sex": self.dcm.PatientSex,
            "Height": float(self.dcm.PatientSize),
            "Weight": int(self.dcm.PatientWeight),
            "Birth Date": format_date(self.dcm.PatientBirthDate),
        }

    @property
    def subject_series(self) -> pd.Series:
        return pd.Series(self.subject_information)

    @property
    def scan_information(self) -> dict:
        return {
            "Patient ID": self.dcm.PatientID,
            "Series Date": format_date(self.dcm.SeriesDate),
            "Series Number": int(self.dcm.SeriesNumber),
            "Series Time": format_time(self.dcm.SeriesTime),
            "Series Description": self.dcm.SeriesDescription,
            "Study Description": self.dcm.StudyDescription,
            "Series UID": self.dcm.SeriesInstanceUID,
            "Origin": os.path.dirname(self.path),
        }

    @property
    def scan_series(self) -> pd.Series:
        return pd.Series(self.scan_information)