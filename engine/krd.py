import pandas as pd


def calculate_krd(priced_cashflows, krd_buckets):
    """
    Calculates bucket-wise Dollar Duration.

    Parameters
    ----------
    priced_cashflows : DataFrame
        Output from pricing.py

    krd_buckets : DataFrame
        KRD_Buckets sheet

    Returns
    -------
    detailed_df
        Cashflows with Dollar Duration and assigned bucket

    bucket_summary
        Dollar Duration by bucket
    """

    df = priced_cashflows.copy()

    # ----------------------------------------
    # Dollar Duration
    # DD = (t * PV) / (1 + y) * 1%
    # ----------------------------------------

    df["Dollar Duration"] = (
        df["Year"]
        * df["Present Value"]
        / (1 + df["Discount Rate"])
        * 0.01
    )

    # Initialise bucket column
    df["Bucket"] = None

    # ----------------------------------------
    # Assign buckets
    # ----------------------------------------

    for _, bucket in krd_buckets.iterrows():

        bucket_name = bucket["Bucket"]

        lower = bucket["Start Year"]

        upper = bucket["End Year"]

        mask = (
            (df["Year"] >= lower)
            &
            (df["Year"] <= upper)
        )

        df.loc[mask, "Bucket"] = bucket_name

    # ----------------------------------------
    # Aggregate Dollar Duration
    # ----------------------------------------

    asset_krd = (
        df.groupby("Bucket", sort=False)["Dollar Duration"]
        .sum()
        .reset_index()
    )

    return df, asset_krd


def calculate_bond_krd(krd_detail):

    bond_krd = (
        krd_detail
        .groupby(
            ["S.No.", "Bucket"],
            sort=False
        )["Dollar Duration"]
        .sum()
        .reset_index()
    )
    
    bond_krd["Total Bond DD"] = (
        bond_krd
        .groupby("S.No.", sort=False)["Dollar Duration"]
        .transform("sum")
    )

    bond_krd["DD Ratio"] = (
        bond_krd["Dollar Duration"]
        /
        bond_krd["Total Bond DD"]
    )

    return bond_krd