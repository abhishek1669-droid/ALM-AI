import pandas as pd


def price_cashflows(cashflows_df, yield_curve_df, curve_name):
    """
    Prices projected cashflows using the selected yield curve.

    Parameters
    ----------
    cashflows_df : DataFrame
        Output from project_cashflows()

    yield_curve_df : DataFrame
        Yield_Curve sheet

    curve_name : str
        Current Valuation / Today / Yesterday / Day Before Yesterday

    Returns
    -------
    DataFrame
        Cashflows with discount rates, discount factors and PVs
    """

    priced_df = cashflows_df.copy()

    for i in priced_df.index:

        year = priced_df.loc[i, "Year"]

        # Fetch the yield corresponding to the cashflow year
        rate = yield_curve_df.loc[
            yield_curve_df["Year"] == year,
            curve_name
        ].values[0]/100

        discount_factor = 1 / ((1 + rate) ** year)

        pv = priced_df.loc[i, "Total Cashflow"] * discount_factor

        priced_df.loc[i, "Discount Rate"] = rate

        priced_df.loc[i, "Discount Factor"] = discount_factor

        priced_df.loc[i, "Present Value"] = pv

    return priced_df