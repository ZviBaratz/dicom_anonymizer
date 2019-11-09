import pandas as pd
import warnings

from pathlib import Path

warnings.simplefilter(action='ignore', category=FutureWarning)


class InformationTable:
    COLUMNS = None
    SHEET_NAME = None
    ID_INDEX = None
    HEADER_COLUMNS = 0
    INDEX_COLUMNS = None

    def __init__(self, data_file):
        self.data_file = self.validate_data_file(data_file)
        self.data = self.load_data()

    def validate_data_file(self, data_file) -> Path:
        if isinstance(data_file, str):
            return Path(data_file)
        elif not isinstance(data_file, Path):
            raise ValueError(
                'data_file must be a valid string or path instance!')
        return data_file

    def load_data(self) -> pd.DataFrame:
        if self.data_file.is_file():
            return pd.read_excel(
                self.data_file,
                sheet_name=self.SHEET_NAME,
                header=self.HEADER_COLUMNS,
                index_col=self.index_col,
                converters={('Raw', 'Patient ID'): str})
        else:
            return pd.DataFrame(columns=self.COLUMNS)

    def get(self, id_value: str) -> pd.DataFrame:
        return self.data[self.data[self.ID_INDEX] == id_value]

    def add(self, row: pd.Series, save: bool = True) -> None:
        self.data = self.data.append(row, ignore_index=True)
        if save:
            self.save()

    def save(self):
        df = self.data.set_index(
            self.INDEX_COLUMNS) if self.INDEX_COLUMNS else self.data
        df.sort_index(inplace=True)
        with pd.ExcelWriter(self.data_file) as writer:
            df.to_excel(writer, sheet_name=self.SHEET_NAME)

    @property
    def index_col(self):
        return [
            self.COLUMNS.index(index_column)
            for index_column in self.INDEX_COLUMNS
        ] if self.INDEX_COLUMNS else 0
