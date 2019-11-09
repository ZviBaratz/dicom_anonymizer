import pandas as pd

from dicom_anonymizer.anonymizer.scan_table import ScanTable
from dicom_anonymizer.anonymizer.subject_table import SubjectTable
from dicom_anonymizer.dicom_handler import DicomHandler
from dicom_anonymizer.tag_faker import TagFaker
from dicom_anonymizer.utils import id_generator, path_generator
from pathlib import Path

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

    def anonymize_dicom(self, dicom_handler: DicomHandler,
                        destination: Path) -> None:
        subject_series = self.subject_table.get_or_create_from_dicom(
            dicom_handler)
        dicom_handler.anonymize_by_series(subject_series)
        dicom_handler.save(destination)
        self.scan_table.get_or_create_from_dicom(dicom_handler)

    def anonymize_tree(self, path: Path, destination: Path):
        dcm_files = path_generator(path, "dcm")
        for dcm_file in dcm_files:
            dicom_handler = DicomHandler(dcm_file)
            if dicom_handler.dcm:
                self.anonymize_dicom(dicom_handler, destination)
            else:
                with open(self.error_log, 'a') as log:
                    log.write(f'Failed to read {dcm_file}!')