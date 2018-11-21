import pydicom

from cryptography.fernet import Fernet

TAGS = ['PatientID', 'PatientName']


class Encrypter:
    def __init__(self, key: bytes, tags: list = TAGS):
        self.key = key
        self.tags = tags
        self.fernet = Fernet(self.key)

    def encrypt_dcm(self, source: str, dest: str):
        dcm = pydicom.dcmread(source)
        for tag is self.tags:
            dcm[tag] = 