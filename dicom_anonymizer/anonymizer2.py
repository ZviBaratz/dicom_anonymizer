import os
import pandas as pd
import pydicom

from dicom_anonymizer.tag_faker import TagFaker
from dicom_anonymizer.utils import format_date, id_generator, format_time
from pathlib import Path
from pydicom.dataset import FileDataset


SUBJECT_COLUMNS = pd.MultiIndex.from_arrays(
    [
        ["Anonymized"] * 3 + ["Raw"] * 11,
        [
            "Patient ID",
            "First Name",
            "Last Name",
            "Patient ID",
            "First Name",
            "Last Name",
            "Sex",
            "Height",
            "Weight",
            "Birth Date",
            "Dominant Hand",
            "Email",
            "Phone Number",
            "Address",
        ],
    ]
)

SCAN_COLUMNS = [
    "Patient ID",
    "Series Date",
    "Series Number",
    "Series Time",
    "Series Description",
    "Study Description",
    "Series UID",
    "Origin",
]


class Anonymizer2:
    def __init__(
        self,
        subjects_key_file: str = "subjects.xlsx",
        scans_key_file: str = "scans.xlsx",
    ):
        self.subjects_key_file = Path(subjects_key_file)
        self.scans_key_file = Path(scans_key_file)
        self.subject_keys = self.load_subject_keys()
        self.scan_keys = self.load_scan_keys()
        self.faker = TagFaker()

    def load_subject_keys(self) -> pd.DataFrame:
        if self.subjects_key_file.is_file():
            df = pd.read_excel(self.subjects_key_file, sheet_name="Subjects")
        else:
            df = pd.DataFrame(columns=SUBJECT_COLUMNS)
        return df

    def load_scan_keys(self) -> pd.DataFrame:
        if not self.scans_key_file.is_file():
            return pd.DataFrame(columns=SCAN_COLUMNS)
        return pd.read_excel(self.scans_key_file, sheet_name="Scans")

    def path_generator(self, path: str, extension: str = "") -> str:
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

    def get_raw_patient_information(self, dcm: FileDataset) -> dict:
        return {
            "Patient ID": dcm.PatientID,
            "First Name": dcm.PatientName.given_name,
            "Last Name": dcm.PatientName.family_name,
            "Sex": dcm.PatientSex,
            "Height": float(dcm.PatientSize),
            "Weight": int(dcm.PatientWeight),
            "Birth Date": format_date(dcm.PatientBirthDate),
        }

    def get_scan_information(self, dcm: FileDataset) -> dict:
        return {
            "Patient ID": dcm.PatientID,
            "Series Date": format_date(dcm.SeriesDate),
            "Series Number": int(dcm.SeriesNumber),
            "Series Time": format_time(dcm.SeriesTime),
            "Series Description": dcm.SeriesDescription,
            "Study Description": dcm.StudyDescription,
            "Series UID": dcm.SeriesInstanceUID,
        }

    def generate_anonymized_information(self, sex: str = None) -> dict:
        last_name, first_name = self.faker.patient_name(sex).split("^")
        return {
            "Patient ID": id_generator(),
            "First Name": first_name,
            "Last Name": last_name,
        }

    def create_subject_series(self, dcm: FileDataset) -> pd.Series:
        raw = self.get_raw_patient_information(dcm)
        anonymized = self.generate_anonymized_information()
        raw = {("Raw", key): value for key, value in raw.items()}
        anonymized = {("Anonymized", key): value for key, value in anonymized.items()}
        raw.update(anonymized)
        return pd.Series(raw)

    def create_scan_series(self, dcm: FileDataset, origin: Path) -> pd.Series:
        s = pd.Series(self.get_scan_information(dcm))
        s["Origin"] = origin
        return s

    def get_existing_subject_row(self, patient_id: str) -> pd.DataFrame:
        return self.subject_keys[self.subject_keys["Raw", "Patient ID"] == patient_id]

    def get_existing_scan_row(self, series_uid: str) -> pd.DataFrame:
        return self.scan_keys[self.scan_keys["Series UID"] == series_uid]

    def create_new_subject_row(self, dcm: FileDataset) -> pd.DataFrame:
        subject_series = self.create_subject_series(dcm)
        self.subject_keys = self.subject_keys.append(subject_series, ignore_index=True)
        self.save_subjects()
        return self.get_existing_subject_row(dcm.PatientID)

    def create_new_scan_row(self, dcm: FileDataset, origin: Path) -> pd.DataFrame:
        scan_series = self.create_scan_series(dcm, origin)
        self.scan_keys = self.scan_keys.append(scan_series, ignore_index=True)
        self.save_scans()
        return self.get_existing_scan_row(dcm.SeriesInstanceUID)

    def get_subject_row(self, dcm: FileDataset) -> pd.DataFrame:
        row = self.get_existing_subject_row(dcm.PatientID)
        if row.empty:
            return self.create_new_subject_row(dcm)
        return row

    def get_scan_row(self, dcm: FileDataset, origin: Path) -> pd.DataFrame:
        row = self.get_existing_scan_row(dcm.SeriesInstanceUID)
        if row.empty:
            return self.create_new_scan_row(dcm, origin)
        return row

    def get_patient_name(self, row: pd.DataFrame) -> str:
        first_name = row["Anonymized"]["First Name"].values[0]
        last_name = row["Anonymized"]["Last Name"].values[0]
        return f"{last_name}^{first_name}"

    def create_file_destination(self, dcm: FileDataset, base_directory: Path) -> Path:
        directory = base_directory / dcm.PatientID / dcm.SeriesInstanceUID
        directory.mkdir(parents=True, exist_ok=True)
        return str(directory / f"{str(dcm.InstanceNumber)}.dcm")

    def anonymize_dcm(self, dcm: FileDataset, base_directory: Path) -> FileDataset:
        row = self.get_subject_row(dcm)
        dcm.PatientID = row["Anonymized"]["Patient ID"].values[0]
        dcm.PatientName = self.get_patient_name(row)
        return dcm

    def save_dcm(self, dcm: FileDataset, base_directory: Path) -> None:
        file_destination = self.create_file_destination(dcm, base_directory)
        dcm.save_as(file_destination)

    def anonymize_tree(self, path: Path, destination: Path):
        dcm_files = self.path_generator(path, "dcm")
        for dcm_file in dcm_files:
            dcm = self.read_dcm(dcm_file)
            anonymized_dcm = self.anonymize_dcm(dcm, destination)
            self.save_dcm(anonymized_dcm, destination)
            self.get_scan_row(dcm, origin=dcm_file.parent)

    def save_subjects(self):
        with pd.ExcelWriter(self.subjects_key_file) as writer:
            self.subject_keys.to_excel(writer, sheet_name="Subjects")

    def save_scans(self):
        df = self.scan_keys.set_index(["Patient ID", "Series Date", "Series Number"])
        with pd.ExcelWriter(self.scans_key_file) as writer:
            df.to_excel(writer, sheet_name="Scans")
