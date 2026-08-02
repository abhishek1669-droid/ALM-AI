import pandas as pd


def prepare_liability_cashflows(liability_df):
    """
    Converts liability cashflows into the same format
    expected by pricing.py.
    """

    df = liability_df.copy()

    df.rename(
        columns={
            "Liability": "Total Cashflow"
        },
        inplace=True
    )

    df["Discount Rate"] = None
    df["Discount Factor"] = None
    df["Present Value"] = None

    return df