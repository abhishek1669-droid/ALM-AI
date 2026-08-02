import pandas as pd


def calculate_dcr(asset_krd, liability_krd):
    """
    Calculates Duration Coverage Ratio (DCR)
    for each KRD bucket.

    Parameters
    ----------
    asset_krd : DataFrame
        Output from asset KRD calculation

    liability_krd : DataFrame
        Output from liability KRD calculation

    Returns
    -------
    DataFrame
        Bucket-wise DCR
    """

    dcr = asset_krd.merge(
        liability_krd,
        on="Bucket",
        suffixes=("_Asset", "_Liability")
    )

    dcr["DCR"] = (
        (dcr["Dollar Duration_Asset"]
        /
        dcr["Dollar Duration_Liability"])*100
    )

    return dcr