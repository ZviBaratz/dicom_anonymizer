import os
import pickle
import pydicom

from dicom_anonymizer.tag_faker import TagFaker
from pydicom.dataset import FileDataset
from tqdm import tqdm


PATIENT_ID_TAG = "PatientID"
VALID_TAGS = [PATIENT_ID_TAG, "PatientName"]


class Anonymizer:
    def __init__(self, associations_file: str = None):
        self.existing_subjects = self.load_associations(associations_file)
        self.faker = TagFaker()

    def load_associations(self, path: str) -> dict:
        """
        Load subject identity associations dictionary from a .pkl key file or return an empty dictionary instance.
        
        Parameters
        ----------
        path : str
            Path to an existing association dictionary saved as a .pkl file.
        
        Returns
        -------
        dict
            Existing subject identity associations.
        """

        if path and os.path.isfile(path):
            with open(path, "rb") as key_file:
                return pickle.load(key_file)
        return dict()

    def update_existing_subjects(self, patient_id: str, **kwargs) -> dict:
        """
        Update associations between subject identities (real unique identifier to fake information).
        
        Parameters
        ----------
        patient_id : str
            Non-anonymized patient unique identifier.
        
        Returns
        -------
        dict
            A dictionary with patient unique identifier as keys and associated fake data as values.
        """

        if patient_id not in self.existing_subjects:
            self.existing_subjects[patient_id] = dict()
        self.existing_subjects[patient_id].update(kwargs)
        return self.existing_subjects

    def get_anonymized_value(self, dcm: FileDataset, tag_name: str) -> str:
        """
        Returns anonymized subject information for a given DICOM header tag. Looks for an existing value
        within existing_subjects, and creates one if none exists.
        
        Parameters
        ----------
        dcm : FileDataset
            DICOM image file.
        tag_name : str
            DICOM header tag name.
        
        Returns
        -------
        str
            Anonymized DICOM header information for this patient.
        
        Raises
        ------
        NotImplementedError
            If the required tag name is not a valid header tag.
        """

        # Try to return existing anonymized information for this patient
        try:
            return self.existing_subjects[dcm.PatientID][tag_name]

        # If none exists, create one
        except KeyError:

            # Anonymized patient unique identifier generation
            if tag_name is PATIENT_ID_TAG:
                new_value = self.faker.patient_id(self.existing_subjects)

            # Anonymized patient name generation
            elif tag_name is "PatientName":

                # Try to generate a name matching the patient's sex
                try:
                    new_value = self.faker.patient_name(dcm.PatientSex)

                # If the PatientSex tag is not defined, simply return a name
                except AttributeError:
                    new_value = self.faker.patient_name()

            # Otherwise, the tag is not valid
            else:
                raise NotImplementedError(
                    f"Invalid DICOM tag name! Expected a value from:\n{VALID_TAGS}\nGot: {tag_name}"
                )

            # Update existing_subjects dictionary to include the generated anonymized information
            self.update_existing_subjects(dcm.PatientID, **{tag_name: new_value})

            # Re-run this method (this time the try block should succeed)
            return self.get_anonymized_value(dcm, tag_name)

    def anonymize_dcm_dataset(
        self, dcm: FileDataset, tag_names: list = VALID_TAGS
    ) -> FileDataset:
        """
        Anonymized DICOM image file header information.
        
        Parameters
        ----------
        dcm : FileDataset
            Buffered DICOM image file.
        tag_names : list, optional
            DICOM header tag names to anonymize, by default VALID_TAGS
        
        Returns
        -------
        FileDataset
            Anonymized DICOM image file.
        """

        # Create a list of tags to anonymize other than the PatientID
        not_patient_id = [tag for tag in tag_names if tag is not PATIENT_ID_TAG]

        # Iterate over the header tags that need to be anonymized
        for tag_name in not_patient_id:
            # Get or generate anonymized value for the current header tag
            anonymized_value = self.get_anonymized_value(dcm, tag_name)
            # Update the DICOM image file
            setattr(dcm, tag_name, anonymized_value)

        # Generate anonymized PatientID and update file
        anonymized_id = self.get_anonymized_value(dcm, PATIENT_ID_TAG)
        dcm.PatientID = anonymized_id

        return dcm

    def create_dcm_path(self, dcm: FileDataset, dest: str) -> str:
        """
        Create a default destination for a given DICOM image within the anonymized destination directory.
        
        Parameters
        ----------
        dcm : FileDataset
            DICOM image file.
        dest : str
            Anonymized destination directory.
        
        Returns
        -------
        str
            Full path for the given DICOM image.
        """

        return os.path.join(
            dest, dcm.PatientID, dcm.SeriesInstanceUID, f"{dcm.InstanceNumber}.dcm"
        )

    def save_dcm(self, dcm: FileDataset, path: str) -> bool:
        """
        Save anonymized DICOM image to a given location.
        
        Parameters
        ----------
        dcm : FileDataset
            DICOM image file.
        path : str
            Full destination path.
        
        Returns
        -------
        bool
            DICOM image save success or failure.
        """

        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            dcm.save_as(path)
            return True
        except Exception:
            print(f"Failed to save DICOM dataset to {path}!")
            return False

    def anonymize_dcm(self, source: str, dest: str) -> bool:
        """
        Read, anonymize, and save a given DICOM image file.
        
        Parameters
        ----------
        source : str
            Source DICOM image path.
        dest : str
            Destination for anonymized DICOM image file.
        
        Returns
        -------
        bool
            Success or failure.
        
        Raises
        ------
        TypeError
            Failure to read the FileDataset from the .dcm file.
        """

        try:
            dcm = pydicom.dcmread(source)
        except pydicom.filereader.InvalidDicomError:
            print(f"Failed to read {source}! Skipping...")
            return False

        dcm = self.anonymize_dcm_dataset(dcm)
        path = self.create_dcm_path(dcm, dest)
        return self.save_dcm(dcm, path)

    def anonymize_tree(self, path: str, dest: str, verbose: bool = True):
        """
        Walk directory tree and anonymize any .dcm files within it.
        
        Parameters
        ----------
        path : str
            Root directory to walk over.
        dest : str
            Destination directory to output anonymized DICOM images to.
        verbose : bool, optional
            Show progressbar, by default True
        """

        n_dcms = len(list(self.path_generator(path, "dcm")))
        dcm_generator = self.path_generator(path, "dcm")
        for dcm_path in tqdm(dcm_generator, disable=not verbose, total=n_dcms):
            self.anonymize_dcm(dcm_path, dest)
        key_file_dest = os.path.join(dest, "key.pkl")
        if verbose:
            print(f"Saving associations to {key_file_dest}...", end="\t")
        self.serialize_associations(key_file_dest)
        if verbose:
            print("done!")

    def serialize_associations(self, path: str) -> bool:
        with open(path, "wb") as key_file:
            pickle.dump(self.existing_subjects, key_file)
            return True

    def path_generator(self, path: str, extension: str = "") -> str:
        for directory, _, files in os.walk(path):
            if extension:
                files = [f for f in files if f.endswith(f".{extension}")]
            for file_name in files:
                yield os.path.join(directory, file_name)

