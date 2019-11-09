import pandas as pd

from dicom_anonymizer.anonymizer.information_table import InformationTable


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