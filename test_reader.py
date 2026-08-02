from engine.excel_reader import ALMData
from engine.cashflows import project_cashflows
from engine.pricing import price_cashflows
from engine.portfolio import build_portfolio
from engine.krd import calculate_krd
from engine.liability import prepare_liability_cashflows
from engine.dcr import calculate_dcr
from engine.krd import calculate_bond_krd
from engine.recommendation import generate_recommendations

curve_name = "day_before_yesterday"

curve_map = {
    "current": "Current Valuation",
    "today": "Today",
    "yesterday": "Yesterday",
    "day_before_yesterday": "Day Before Yesterday"
}

selected_curve = curve_map[curve_name]

data = ALMData("ALM_Data.xlsx").load()

cashflows = project_cashflows(data.assets)

priced_current = price_cashflows(
    cashflows,
    data.yield_curve,
    "Current Valuation"
)

portfolio_current = build_portfolio(
    data.assets,
    priced_current
)

priced_market = price_cashflows(
    cashflows,
    data.yield_curve,
    selected_curve
)

portfolio_market = build_portfolio(
    data.assets,
    priced_market
)


krd_detail, asset_krd = calculate_krd(
    priced_market,
    data.krd_buckets
)


liability_cf = prepare_liability_cashflows(
    data.liabilities
)

priced_liabilities = price_cashflows(
    liability_cf,
    data.yield_curve,
    selected_curve
)

_, liability_krd = calculate_krd(
    priced_liabilities,
    data.krd_buckets
)

dcr = calculate_dcr(
    asset_krd,
    liability_krd
)

bond_krd = calculate_bond_krd(krd_detail)

recommendation_df, rejected_df, message = generate_recommendations(
    portfolio_current,
    portfolio_market,
    asset_krd,
    liability_krd,
    dcr,
    bond_krd)

print(len(recommendation_df))
print(len(rejected_df))
print(message)

print(recommendation_df.iloc[0])

print(recommendation_df.iloc[0]["Base DCR"])