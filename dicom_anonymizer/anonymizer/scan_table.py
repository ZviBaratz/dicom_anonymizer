import pandas as pd

from dicom_anonymizer.anonymizer.information_table import InformationTable
from dicom_anonymizer.dicom_handler import DicomHandler


class ScanTable(InformationTable):
    COLUMNS = [
        "Patient ID",
        "Series Date",
        "Series Number",
        "Series Time",
        "Series Description",
        "Study Description",
        "Series UID",
        "Origin",
    ]
    SHEET_NAME = 'Scans'
    ID_INDEX = 'Series UID'
    INDEX_COLUMNS = [
        "Patient ID",
        "Series Date",
        "Series Number",
    ]

    def load_data(self) -> pd.DataFrame:
        return super().load_data().reset_index()

    def get_or_create_from_dicom(self, dicom_handler: DicomHandler):
        series = self.get(dicom_handler.scan_id)
        if series.empty:
            return self.add(dicom_handler.scan_series, save=True)
        return series
