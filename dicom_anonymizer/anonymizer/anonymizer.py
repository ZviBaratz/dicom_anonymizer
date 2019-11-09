import os
import pandas as pd
import pydicom

from dicom_anonymizer.anonymizer.scan_table import ScanTable
from dicom_anonymizer.anonymizer.subject_table import SubjectTable
from dicom_anonymizer.tag_faker import TagFaker
from dicom_anonymizer.utils import format_date, id_generator, format_time
from pathlib import Path
from pydicom.dataset import FileDataset

SUBJECTS_FILE = "subjects.xlsx"
SCANS_FILE = "scans.xlsx"
ERROR_LOG = "errors.log"


class Anonymizer:
    def __init__(self,
                 subjects_file=SUBJECTS_FILE,
                 scans_file=SCANS_FILE,
                 error_log: str = ERROR_LOG):
        self.subject_table = SubjectTable(subjects_file)
        self.scan_table = ScanTable(scans_file)
        self.error_log = error_log
        self.faker = TagFaker()

    def path_generator(self, path: str, extension: str = "dcm") -> str:
        for directory, _, files in os.walk(path):
            if extension:
                files = [f for f in files if f.endswith(f".{extension}")]
            for file_name in files:
                yield Path(directory, file_name)

    def read_dcm(self, path: Path) -> FileDataset:
        try:
            return pydicom.read_file(str(path))
        except pydicom.filereader.InvalidDicomError:
            print(f"Failed to read {path}! Skipping...")

    def get_subject_information(self, dcm: FileDataset) -> dict:
        return {
            "Patient ID": dcm.PatientID,
            "First Name": dcm.PatientName.given_name,
            "Last Name": dcm.PatientName.family_name,
            "Sex": dcm.PatientSex,
            "Height": float(dcm.PatientSize),
            "Weight": int(dcm.PatientWeight),
            "Birth Date": format_date(dcm.PatientBirthDate),
        }

    def get_scan_information(self, dcm: FileDataset, origin: str) -> dict:
        return {
            "Patient ID": dcm.PatientID,
            "Series Date": format_date(dcm.SeriesDate),
            "Series Number": int(dcm.SeriesNumber),
            "Series Time": format_time(dcm.SeriesTime),
            "Series Description": dcm.SeriesDescription,
            "Study Description": dcm.StudyDescription,
            "Series UID": dcm.SeriesInstanceUID,
            "Origin": origin,
        }

    def generate_anonymized_information(self, sex: str = None) -> dict:
        fake_name = self.faker.patient_name(sex)
        last_name, first_name = fake_name.split("^")
        return {
            "Patient ID": id_generator(),
            "First Name": first_name,
            "Last Name": last_name,
        }

    def create_subject_row(self, dcm: FileDataset) -> pd.Series:
        raw = self.get_subject_information(dcm)
        anonymized = self.generate_anonymized_information()
        raw = {("Raw", key): value for key, value in raw.items()}
        anonymized = {("Anonymized", key): value
                      for key, value in anonymized.items()}
        raw.update(anonymized)
        return pd.Series(raw)

    def create_scan_row(self, dcm: FileDataset, origin: Path) -> pd.Series:
        return pd.Series(self.get_scan_information(dcm, origin))

    def add_subject(self, dcm: FileDataset) -> pd.DataFrame:
        subject_series = self.create_subject_row(dcm)
        self.subject_table.add(subject_series, save=True)
        return self.subject_table.get(dcm.PatientID)

    def add_scan(self, dcm: FileDataset, origin: Path) -> pd.DataFrame:
        scan_series = self.create_scan_row(dcm, origin)
        self.scan_table.add(scan_series, save=True)
        return self.scan_table.get(dcm.SeriesInstanceUID)

    def get_subject_row(self, dcm: FileDataset) -> pd.DataFrame:
        row = self.subject_table.get(dcm.PatientID)
        if row.empty:
            return self.add_subject(dcm)
        return row

    def get_scan_row(self, dcm: FileDataset, origin: Path) -> pd.DataFrame:
        row = self.scan_table.get(dcm.SeriesInstanceUID)
        if row.empty:
            return self.add_scan(dcm, origin)
        return row

    def get_patient_name(self, row: pd.DataFrame) -> str:
        first_name = row["Anonymized"]["First Name"].values[0]
        last_name = row["Anonymized"]["Last Name"].values[0]
        return f"{last_name}^{first_name}"

    def create_file_destination(self, dcm: FileDataset,
                                base_directory: Path) -> Path:
        directory = base_directory / dcm.PatientID / dcm.SeriesInstanceUID
        directory.mkdir(parents=True, exist_ok=True)
        return directory / f"{str(dcm.InstanceNumber)}.dcm"

    def anonymize_dcm(self, dcm: FileDataset) -> FileDataset:
        row = self.get_subject_row(dcm)
        dcm.PatientID = row["Anonymized"]["Patient ID"].values[0]
        dcm.PatientName = self.get_patient_name(row)
        return dcm

    def save_dcm(self, dcm: FileDataset, base_directory: Path) -> None:
        file_destination = self.create_file_destination(dcm, base_directory)
        if file_destination.is_file():
            relative = str(file_destination)[len(str(base_directory)):]
            print(f'{relative} exists! skipping...')
        else:
            dcm.save_as(str(file_destination))

    def anonymize_tree(self, path: Path, destination: Path):
        dcm_files = self.path_generator(path, "dcm")
        for dcm_file in dcm_files:
            dcm = self.read_dcm(dcm_file)
            if dcm:
                anonymized_dcm = self.anonymize_dcm(dcm)
                self.save_dcm(anonymized_dcm, destination)
                self.get_scan_row(dcm, origin=dcm_file.parent)
            else:
                with open(self.error_log, 'a') as log:
                    log.write(f'Failed to read {dcm_file}!')