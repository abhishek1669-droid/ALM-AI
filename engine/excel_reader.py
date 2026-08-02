import pandas as pd


class ALMData:

    def __init__(self, file_path):

        self.file_path = file_path

        self.assets = None
        self.liabilities = None
        self.yield_curve = None
        self.krd_buckets = None

    def load(self):

        self.assets = pd.read_excel(
            self.file_path,
            sheet_name="Asset"
        )

        self.liabilities = pd.read_excel(
            self.file_path,
            sheet_name="Liabilities"
        )

        self.yield_curve = pd.read_excel(
            self.file_path,
            sheet_name="Yield_Curve"
        )

        self.krd_buckets = pd.read_excel(
            self.file_path,
            sheet_name="KRD_Buckets"
        )

        return self