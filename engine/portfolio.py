import pandas as pd


def build_portfolio(asset_df, priced_cashflows):
    """
    Builds a bond-level portfolio summary.

    Parameters
    ----------
    asset_df : DataFrame
        Original Asset sheet

    priced_cashflows : DataFrame
        Output from pricing.py

    Returns
    -------
    DataFrame
        One row per bond
    """

    # Sum present values for each bond
    prices = (
        priced_cashflows
        .groupby("S.No.")["Present Value"]
        .sum()
        .reset_index()
    )

    prices.rename(
        columns={"Present Value": "Bond Price"},
        inplace=True
    )

    # Merge with original asset data
    portfolio = asset_df.merge(
        prices,
        on="S.No.",
        how="left"
    )

    return portfolio