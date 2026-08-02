import pandas as pd


def project_cashflows(asset_df):
    """
    Generates yearly cashflows for all bonds in the portfolio.

    Parameters
    ----------
    asset_df : pandas.DataFrame
        Asset sheet from Excel

    Returns
    -------
    pandas.DataFrame
        Year-wise cashflow projection
    """

    cashflow_list = []

    for _, bond in asset_df.iterrows():

        bond_id = bond["S.No."]
        tenure = int(bond["Tenure"])
        nominal = bond["Nominal Value"]
        coupon_rate = bond["Coupon Rate(%)"]

        annual_coupon = nominal * coupon_rate

        for year in range(1, tenure + 1):

            principal = nominal if year == tenure else 0

            total_cf = annual_coupon + principal

            cashflow_list.append({

                "S.No.": bond_id,

                "Year": year,

                "Coupon": annual_coupon,

                "Principal": principal,

                "Total Cashflow": total_cf,

                "Discount Rate": None,

                "Discount Factor": None,

                "Present Value": None

            })

    cashflows = pd.DataFrame(cashflow_list)

    return cashflows