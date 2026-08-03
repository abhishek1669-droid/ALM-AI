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
from conversation_state import conversation_state
from engine.system_prompt import SYSTEM_PROMPT

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


def run_recommendation(curve_name):

    curve_map = {
        "current": "Current Valuation",
        "today": "Today",
        "yesterday": "Yesterday",
        "day before yesterday": "Day Before Yesterday"
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
    # ----------------------------
    # Update conversation memory
    # ----------------------------

    conversation_state["last_tool"] = "recommendation"
    conversation_state["last_curve"] = curve_name

    conversation_state["last_recommendation_df"] = recommendation_df
    conversation_state["last_rejected_df"] = rejected_df

    if len(recommendation_df) > 0:

        top = recommendation_df.iloc[0]

        conversation_state["recommendation_summary"] = {

            "Sell Bond": top["Sell Bond"],

            "Buy Bond": top["Buy Bond"],

            "Expected Gain": top["Expected Gain"],

            "Deviation Improvement": top["Deviation Improvement"]

        }

    else:

        conversation_state["recommendation_summary"] = None

    if len(recommendation_df) > 0:

        conversation_state["last_sell_bond"] = recommendation_df.iloc[0]["Sell Bond"]

        conversation_state["last_buy_bond"] = recommendation_df.iloc[0]["Buy Bond"]

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
        model="gemini-2.5-flash",
        contents=f"""{SYSTEM_PROMPT}

    User Question:
    {user_query}
    """
    )

    return {

        "response": response.text,

        "recommendation_df": recommendation_df,

        "rejected_df": rejected_df,

        "summary": conversation_state["recommendation_summary"],

        "curve": curve_name,

        "follow_up": False

    }



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
    - Duration Coverage Ratio (DCR)
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

    1. If the user mentions "today" or "today's", return "today".
    2. If the user mentions "yesterday" or "yesterday's", return "yesterday".
    3. If the user mentions "day before yesterday" or "day before yesterday's", return "day before yesterday".
    4. If no curve is mentioned, return an empty string "".
    5. If the user is asking about a previous recommendation
    (for example: "show sell bond", "buy bond details",
    "why this strategy", "show details", "its KRD"),
    still return tool = "recommendation".
    6. Do not invent any other curve names.
    7. Do not define any acronym on your own.
    8. Strictly define DCR as Duration Coverage Ratio and KRD as Key Rate Duration.

    If the user is asking about the previous answer, for example:

    - Which bond should I sell?
    - Which bond should I buy?
    - Show sell bond.
    - Show buy bond.
    - Why was this selected?
    - Explain this recommendation.
    - Show rejected strategies.
    - Show details.

    then set

    "follow_up": true

    Otherwise

    "follow_up": false

    Return ONLY valid JSON.

    Example:

    {{
        "tool": "recommendation",
        "curve": "today",
        "follow_up": false
    }}

    User Question:

    {user_query}
    """

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt
    )

    return json.loads(response.text)


def dataframe_to_text(df):

    if df is None or len(df) == 0:
        return "No data available."

    rows = []

    for _, row in df.iterrows():

        row_text = []

        for column in df.columns:
            row_text.append(f"{column}: {row[column]}")

        rows.append(" | ".join(row_text))

    return "\n".join(rows)


def explain_followup(user_query):

    recommendation_df = conversation_state["last_recommendation_df"]
    rejected_df = conversation_state["last_rejected_df"]

    if recommendation_df is None:
        return "No previous recommendation available."

    curve = conversation_state["last_curve"]

    summary = conversation_state["recommendation_summary"]
    
    recommended_text = dataframe_to_text(recommendation_df)
    rejected_text = dataframe_to_text(rejected_df)

    prompt = f"""
    You are Arjuna AI.

    The user is asking a follow-up question regarding the PREVIOUS recommendation.

    The recommendation engine has ALREADY been executed.

    Do NOT generate a fresh recommendation.

    Use ONLY the information below.

    ====================================================

    Yield Curve Used

    {curve}

    ====================================================
    
    Recommendation Summary

    {summary}

    ====================================================

    All Recommended Strategies

    {recommended_text}

    ====================================================

    Rejected Strategies

    {rejected_text}

    ====================================================

    User Question

    {user_query}

    ====================================================

    Instructions

    1. Answer ONLY using the stored recommendation.

    2. If the answer exists in the recommendation,
    answer directly.

    3. If the user asks why a strategy was rejected,
    use the rejected strategies.

    4. Never generate a fresh recommendation.

    5. Never assume values that are not available.

    6. If the requested information is unavailable,
    state that politely.
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"""{SYSTEM_PROMPT}

    User Question:
    {user_query}
    """
    )

    return {

        "response": response.text,

        "recommendation_df": conversation_state["last_recommendation_df"],

        "rejected_df": conversation_state["last_rejected_df"],

        "summary": conversation_state["recommendation_summary"],

        "curve": conversation_state["last_curve"],

        "follow_up": True

    }


def ask_arjuna(user_query):

    intent = identify_tool(user_query)

    tool = intent["tool"]
    curve = intent["curve"]
    follow_up = intent["follow_up"]

    if curve == "":
        curve = conversation_state["last_curve"]

    print(f"Tool Selected: {tool}")

    if tool == "recommendation":

        if follow_up:

            return explain_followup(user_query)

        else:

            return explain_recommendation(curve, user_query)

    elif tool == "pricing":
        
        return {

            "response": "Pricing tool not yet connected.",

            "recommendation_df": None,

            "rejected_df":None,

            "summary": None,

            "curve": None,

            "follow_up": None

        }


    elif tool == "dcr":

        return {

            "response": "DCR tool not yet connected.",

            "recommendation_df": None,

            "rejected_df":None,

            "summary": None,

            "curve": None,

            "follow_up": None

        }


    elif tool == "krd":

        return {

            "response": "KRD tool not yet connected.",

            "recommendation_df": None,

            "rejected_df":None,

            "summary": None,

            "curve": None,

            "follow_up": None

        }

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

        return {

            "response": response.text,

            "recommendation_df": None,

            "rejected_df":None,

            "summary": None,

            "curve": None,

            "follow_up": None

        }

#question = input("Ask Arjuna AI: ")

#print(ask_arjuna(question))
if __name__ == "__main__":    
    while True:

        question = input("\nAsk Arjuna AI: ")

        if question.lower() == "exit":
            break

        response = ask_arjuna(question)

        print(response)