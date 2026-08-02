import os
import json
from google import genai

from engine.excel_reader import ALMData
from engine.cashflows import project_cashflows
from engine.pricing import price_cashflows
from engine.portfolio import build_portfolio
from engine.krd import calculate_krd
from engine.liability import prepare_liability_cashflows
from engine.dcr import calculate_dcr
from engine.krd import calculate_bond_krd
from engine.recommendation import generate_recommendations

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


def run_recommendation(curve_name):

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

    return recommendation_df, rejected_df, message


def explain_recommendation(curve_name,user_query):

    recommendation_df, rejected_df, message = run_recommendation(curve_name)

    if recommendation_df.empty and rejected_df.empty:

        prompt = f"""
        The recommendation engine returned no recommendation.

        Reason:
        {message}

        Explain this to the user in simple language.
        """

    else:

        top_strategy = recommendation_df.iloc[0].to_dict()

        prompt = f"""
        You are an ALM expert.

        The recommendation engine has produced the following recommendation.

        {top_strategy}

        If the user asks:
        - Which bond should I sell? → Tell only the sell bond.
        - Which bond should I buy? → Tell only the purchase bond.
        - What is the MTM gain? → Tell only the MTM gain.
        - Ask for a recommendation? → Explain the complete strategy.

        Never invent values. Use only the supplied data.
        """

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt
    )

    return response.text


def identify_tool(user_query):

    prompt = f"""
    Your job is to identify:

    1. Which tool should be called.
    2. Which yield curve should be used.

    Available tools:

    1. recommendation
    - portfolio switching
    - bond switching
    - rebalance
    - optimization
    - DCR improvement
    - sell and buy bonds

    2. pricing
    - market value
    - valuation
    - present value
    - price
    - valuation of bonds

    3. dcr
    - DCR
    - duration gap
    - duration matching

    4. krd
    - key rate duration
    - KRD
    - bucket duration

    5. general
    - greetings
    - actuarial concepts
    - finance concepts
    - anything else

    Available curves:

    - today's
    - yesterday's
    - day before yesterday's

    Rules:

    1. If the user mentions today's → return "today".
    2. If the user mentions yesterday's → return "yesterday".
    3. If the user mentions day before yesterday's → return "day before yesterday".
    4. If no curve is mentioned, return "today".
    5. Do not invent any other curve names.

    Return ONLY valid JSON.

    Example:

    {{
        "tool": "recommendation",
        "curve": "today"
    }}

    User Question:

    {user_query}
    """

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt
    )

    return json.loads(response.text)


def ask_arjuna(user_query):

    intent = identify_tool(user_query)

    tool = intent["tool"]

    curve = intent["curve"]

    print(f"Tool Selected: {tool}")

    if tool == "recommendation":

        return explain_recommendation(curve, user_query)

    elif tool == "pricing":

        return "Pricing tool not yet connected."

    elif tool == "dcr":

        return "DCR tool not yet connected."

    elif tool == "krd":

        return "KRD tool not yet connected."

    else:

        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=f"""
            You are Arjuna AI.

            Respond in the context of Asset-Liability Management (ALM), actuarial science, Investments and Finance.

            User Question:

            {user_query}
            """
        )

        return response.text

question = input("Ask Arjuna AI: ")

print(ask_arjuna(question))