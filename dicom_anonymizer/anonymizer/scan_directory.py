import pandas as pd

from dicom_anonymizer.dicom_handler import DicomHandler
from pathlib import Path


class ScanDirectory:
    COLUMNS = [
        "Series Date",
        "Series Number",
        "Series Time",
        "Series Description",
        "Study Description",
        "Series UID",
        "Origin",
    ]
    SHEET_NAME = 'Scans'
    INDEX_COLUMNS = [
        "Series Date",
        "Series Number",
    ]

    def __init__(self, path: Path):
        self.path = path if isinstance(path, Path) else Path(path)

    def get_patient_file(self, patient_id: str) -> Path:
        return self.path / (patient_id + '.xlsx')

    def get_patient_data(self, patient_id: str) -> pd.DataFrame:
        path = self.get_patient_file(patient_id)
        try:
            return pd.read_excel(
                path,
                sheet_name=self.SHEET_NAME,
                header=0,
                index_col=self.index_col,
            ).reset_index()
        except FileNotFoundError:
            return pd.DataFrame(columns=self.COLUMNS)

    def has(self, patient_data: pd.DataFrame, scan_id: str) -> bool:
        scan_data = patient_data[patient_data['Series UID'] == scan_id]
        return not scan_data.empty

    def add(self,
            patient_id: str,
            patient_data: pd.DataFrame,
            scan_information: dict,
            save: bool = True) -> pd.DataFrame:
        patient_data = patient_data.append(scan_information, ignore_index=True)
        if save:
            self.save(patient_id, patient_data)
        return patient_data

    def save(self, patient_id: str, patient_data: pd.DataFrame):
        patient_file = self.get_patient_file(patient_id)
        patient_data = patient_data.set_index(self.INDEX_COLUMNS)
        patient_data = patient_data.sort_index().drop(
            'index', axis=1, errors='ignore')
        with pd.ExcelWriter(patient_file) as writer:
            patient_data.to_excel(writer, sheet_name=self.SHEET_NAME)

    def create_from_dicom(self,
                          dicom_handler: DicomHandler,
                          ignore_existing: bool = True) -> None:
        patient_data = self.get_patient_data(dicom_handler.subject_id)
        scan_id = dicom_handler.scan_information['Series UID']
        if not self.has(patient_data, scan_id):
            self.add(
                dicom_handler.subject_id,
                patient_data,
                dicom_handler.scan_information,
                save=True)
        elif not ignore_existing:
            raise ValueError(f'Information for scan{scan_id} already exists!')

    @property
    def index_col(self):
        return [
            self.COLUMNS.index(index_column)
            for index_column in self.INDEX_COLUMNS
        ] if self.INDEX_COLUMNS else 0
