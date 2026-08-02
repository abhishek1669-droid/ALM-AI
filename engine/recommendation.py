import pandas as pd


def generate_recommendations(
    portfolio_current,
    portfolio_market,
    asset_krd,
    liability_krd,
    dcr,
    bond_krd
):
    """
    Generate portfolio switch recommendations.

    Parameters
    ----------
    portfolio_current : DataFrame
        Portfolio valued using Current Valuation curve.

    portfolio_market : DataFrame
        Portfolio valued using selected market curve
        (Today / Yesterday / Day Before Yesterday).

    asset_krd : DataFrame
        Asset KRD by bucket.

    liability_krd : DataFrame
        Liability KRD by bucket.

    dcr : DataFrame
        Duration Coverage Ratio by bucket.

    bond_krd : DataFrame
        Bond-wise KRD contribution.

    Returns
    -------
    switch_df : DataFrame
    """

    # -----------------------------------------
    # STEP 1 : Merge current and market values
    # -----------------------------------------

    switch_df = portfolio_current.merge(
        portfolio_market,
        on="S.No.",
        suffixes=("_book", "_market")
    )

    # -----------------------------------------
    # STEP 2 : Calculate MTM
    # -----------------------------------------

    switch_df["MTM"] = (
        switch_df["Bond Price_market"]
        - switch_df["Bond Price_book"]
    )

    # -----------------------------------------
    # STEP 3 : Identify surplus and deficit buckets
    # -----------------------------------------

    # ============================================================
    # Bond to Home Bucket Mapping
    # ============================================================

    bucket_order = [
        "0-6",
        "7-10",
        "11-18",
        "19-26",
        "27-32",
        "33-40",
        ">41"
    ]

    bond_mapping = (
        switch_df[["S.No."]]
        .sort_values("S.No.")
        .reset_index(drop=True)
    )

    bond_mapping["Bucket"] = bucket_order

    surplus_buckets = dcr.loc[
        dcr["DCR"] > 100,
        "Bucket"
    ].tolist()

    deficit_buckets = dcr.loc[
        dcr["DCR"] < 100,
        "Bucket"
    ].tolist()

    switch_df = switch_df.merge(
        bond_mapping,
        on="S.No.",
        how="left"
    )

    switch_df["Sale Candidate"] = (
        switch_df["Bucket"].isin(surplus_buckets)
    ) & (
        switch_df["MTM"] > 0
    )

    sale_candidates = switch_df[
        switch_df["Sale Candidate"]
    ].copy()

    purchase_buckets = dcr[
        dcr["Bucket"].isin(deficit_buckets)
    ].copy()

    # ============================================================
    # STEP 4 : Loop through each purchase bucket
    # ============================================================

    recommendations = []
    rejected_recommendations = []

    for _, purchase_row in purchase_buckets.iterrows():

        purchase_bucket = purchase_row["Bucket"]

        # Asset DD in purchase bucket
        asset_dd = asset_krd.loc[
            asset_krd["Bucket"] == purchase_bucket,
            "Dollar Duration"
        ].iloc[0]

        # Liability DD in purchase bucket
        liability_dd = liability_krd.loc[
            liability_krd["Bucket"] == purchase_bucket,
            "Dollar Duration"
        ].iloc[0]

        # DD deficit
        dd_gap = liability_dd - asset_dd

        if dd_gap > 0:

        # ============================================================
        # Loop through each purchase bond in the deficit bucket
        # ============================================================

            # Purchase bond corresponding to this bucket
            purchase_bond = bond_mapping.loc[
                bond_mapping["Bucket"] == purchase_bucket,
                "S.No."
            ].iloc[0]

            # DD Ratio of purchase bond in its own bucket
            purchase_dd_ratio = bond_krd.loc[
                (bond_krd["S.No."] == purchase_bond) &
                (bond_krd["Bucket"] == purchase_bucket),
                "DD Ratio"
            ].iloc[0]

            # Investment amount required
            purchase_amount = dd_gap / purchase_dd_ratio

            # ========================================================
            # Loop through each sell candidate
            # ========================================================

            for _, sell_row in sale_candidates.iterrows():

                sell_bond = sell_row["S.No."]

                sell_market_value = sell_row["Bond Price_market"]

                # Skip if bond is too small
                if purchase_amount > sell_market_value:
                    continue

                # Proportion of the bond to be sold
                sell_proportion = purchase_amount / sell_market_value

                # expected gain
                expected_gain = sell_proportion * sell_row["MTM"]

                # Create temporary Asset DD table
                temp_asset = asset_krd.copy()
                # ============================================================
                # Update Asset DD for every bucket
                # ============================================================

                for idx in temp_asset.index:

                    current_bucket = temp_asset.loc[idx, "Bucket"]

                    # DD Ratio of sell bond in this bucket
                    sell_dd_ratio = bond_krd.loc[
                        (bond_krd["S.No."] == sell_bond) &
                        (bond_krd["Bucket"] == current_bucket),
                        "DD Ratio"
                    ]

                    if sell_dd_ratio.empty:
                        sell_dd_ratio = 0
                    else:
                        sell_dd_ratio = sell_dd_ratio.iloc[0]

                    # DD Ratio of purchase bond in this bucket
                    purchase_dd_ratio_bucket = bond_krd.loc[
                        (bond_krd["S.No."] == purchase_bond) &
                        (bond_krd["Bucket"] == current_bucket),
                        "DD Ratio"
                    ]

                    if purchase_dd_ratio_bucket.empty:
                        purchase_dd_ratio_bucket = 0
                    else:
                        purchase_dd_ratio_bucket = purchase_dd_ratio_bucket.iloc[0]

                    # Update Asset DD
                    temp_asset.loc[idx, "Dollar Duration"] = (
                        temp_asset.loc[idx, "Dollar Duration"]
                        - (sell_dd_ratio * purchase_amount)
                        + (purchase_dd_ratio_bucket * purchase_amount)
                    )

                # ============================================================
                # Calculate New DCR
                # ============================================================

                temp_dcr = temp_asset.merge(

                    liability_krd,

                    on="Bucket",

                    suffixes=("_Asset", "_Liability")

                )

                temp_dcr["New DCR"] = (

                    temp_dcr["Dollar Duration_Asset"]

                    /

                    temp_dcr["Dollar Duration_Liability"]

                ) * 100

                # ============================================================
                # Base portfolio deviation
                # ============================================================

                base_dcr = dcr.copy()

                base_dcr["Deviation"] = abs(base_dcr["DCR"] - 100)

                base_total_deviation = base_dcr["Deviation"].sum()

                # ============================================================
                # Calculate DCR Improvement
                # ============================================================

                temp_dcr["Deviation"] = abs(temp_dcr["New DCR"] - 100)

                new_total_deviation = temp_dcr["Deviation"].sum()

                deviation_improvement = (
                    base_total_deviation - new_total_deviation
                )

                improvement_pct = (
                    deviation_improvement / base_total_deviation
                ) * 100

                # ============================================================
                # Reject strategy if DCR does not improve
                # ============================================================

                if deviation_improvement < 0:

                    rejected_recommendations.append({

                        "Sell Bond": sell_bond,

                        "Buy Bond": purchase_bond,

                        "Purchase Amount": purchase_amount,

                        "expected Gain": expected_gain,

                        "Deviation Improvement": deviation_improvement,

                        "Improvement %": improvement_pct,

                        "Reason": "Overall DCR deviation did not improve"

                    })

                    continue

                # ============================================================
                # Store Accepted Recommendation
                # ============================================================

                recommendations.append({

                    "Sell Bond": sell_bond,

                    "Buy Bond": purchase_bond,

                    "Sell Bucket": sell_row["Bucket"],

                    "Purchase Bucket": purchase_bucket,

                    "Purchase Amount": purchase_amount,

                    "Sell Proportion": sell_proportion,

                    "Expected Gain": expected_gain,

                    "Deviation Improvement": deviation_improvement,

                    "Improvement %": improvement_pct,

                    "Base DCR": dcr.copy(),

                    "New DCR": temp_dcr.copy()

                })
                
    if sale_candidates.empty:
        return (
            pd.DataFrame(),
            pd.DataFrame(),
            "No MTM gain available on bonds for the selected yield curve."
        )
    
    else:
    
        recommendation_df = pd.DataFrame(recommendations)

        recommendation_df = recommendation_df.sort_values(

            by=[

                "Expected Gain",

                "Deviation Improvement"

            ],

            ascending=[False, False]

        ).reset_index(drop=True)

        rejected_df = pd.DataFrame(rejected_recommendations)

        return recommendation_df, rejected_df, _