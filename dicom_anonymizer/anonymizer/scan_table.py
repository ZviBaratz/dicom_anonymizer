import pandas as pd

from dicom_anonymizer.anonymizer.information_table import InformationTable


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