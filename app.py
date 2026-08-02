import streamlit as st

st.set_page_config(
    page_title="Arjuna AI",
    page_icon="🏹",
    layout="wide"
)

st.title("🏹 Arjuna AI")
st.caption("AI Copilot for Asset Liability Management")

st.divider()

left_col, right_col = st.columns([1, 1.4])

question = st.chat_input("Ask Arjuna AI...")

with left_col:

    if question:
        with st.chat_message("user"):
            st.write(question)

        with st.chat_message("assistant"):

            with st.spinner("Arjuna AI is thinking..."):

                from test_recommendation import ask_arjuna

                result = ask_arjuna(question)

                st.subheader("Arjuna AI")

                st.write(result["response"])

with right_col:
    if question:
        summary = result["summary"]

        if summary is not None:

            st.subheader("📊 Recommendation Summary")

            col1, col2 = st.columns(2)

            with col1:

                st.metric(
                    "Sell Bond ID",
                    summary["Sell Bond"]
                )

                st.metric(
                    "Expected Gain",
                    round(summary["Expected Gain"], 2)
                )

            with col2:

                st.metric(
                    "Buy Bond ID",
                    summary["Buy Bond"]
                )

                st.metric(
                    "Deviation Improvement",
                    round(summary["Deviation Improvement"], 2)
                )

        st.divider()

        st.subheader("📋 Recommended Strategies")

        st.dataframe(
            result["recommendation_df"],
            use_container_width=True,
            hide_index=True
        )
