import glob
import os
import pickle
import pydicom

from cryptography.fernet import Fernet


DESTINATION = "/media/zvi/Data/Data/Encrypted MRI"
TAGS = ["PatientID", "PatientName", "PatientBirthDate"]
ASSOCIATION_FILE = os.path.join(DESTINATION, "associations.pkl")


class Encrypter:
    def __init__(self, key: bytes, tags: list = TAGS):
        self.key = key
        self.tags = tags
        self.fernet = Fernet(self.key)
        self.associations = self.read_associations()

    def read_associations(self, path: str = ASSOCIATION_FILE):
        try:
            with open(path, "rb") as associations:
                return pickle.load(associations)
        except FileNotFoundError:
            return {}

    def save_associations(self, associations_dict: dict, path: str = ASSOCIATION_FILE):
        with open(path, "wb") as associations:
            pickle.dump(associations_dict, associations)

    def create_association(self, subject_identifier: str):
        if self.associations:
            if subject_identifier in self.associations:
                raise ValueError(f"Identifier {subject_identifier} already exists!")
            last_value = max([int(value) for value in self.associations.values()])
            new_value = str(last_value + 1).zfill(6)
        else:
            new_value = "1".zfill(6)
        self.associations[subject_identifier] = new_value
        self.save_associations(self.associations)
        return new_value

    def get_subject_number(self, subject_identifier: str):
        try:
            return self.associations[subject_identifier]
        except KeyError:
            return self.create_association(subject_identifier)

    def get_default_dcm_path(
        self, dcm: pydicom.dataset.Dataset, dest: str = DESTINATION
    ):
        subject_number = self.get_subject_number(dcm.PatientID)
        series_uid = str(dcm.SeriesInstanceUID)
        file_name = str(dcm.InstanceNumber) + ".dcm"
        return os.path.join(dest, subject_number, series_uid, file_name)

    def encrypt_dcm(self, source: str, dest: str = DESTINATION):
        print(f"\n{source}:")
        print("Reading data...", end="\t")
        dcm = pydicom.dcmread(source)
        print("\u2714")

        file_dest = self.get_default_dcm_path(dcm, dest)
        if os.path.isfile(file_dest):
            print("\u2716\t[Exists!]")
            return

        for tag in self.tags:
            print(f"Encrypting {tag}...", end="\t")
            value = bytes(str(dcm.get(tag)), "utf-8")
            encrypted_value = self.fernet.encrypt(value)
            dcm.data_element(tag).value = encrypted_value
            print("\u2714")

        print(f"Saving encrypted dcm to {file_dest}...", end="\t")
        try:
            file_dir = os.path.dirname(file_dest)
            os.makedirs(file_dir, exist_ok=True)
            dcm.save_as(file_dest)
            print("\u2714")
        except Exception as e:
            print("\u2716")
            print(e.args)

    def encrypt_dir(self, path: str):
        pattern = os.path.join(path, "**/*.dcm")
        dcms = glob.iglob(pattern, recursive=True)
        for dcm in dcms:
            self.encrypt_dcm(dcm)
