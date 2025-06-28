
import streamlit as st
import pandas as pd

st.set_page_config(page_title="FundSight AI", layout="wide")
st.title("Nonprofit Finance Insights")

uploaded_file = st.file_uploader("Upload QuickBooks CSV Export", type=["csv"])
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.subheader("Data Preview")
    st.dataframe(df.head())

    if st.button("Generate Insights"):
        income = df[df["Amount"] > 0]["Amount"].sum()
        expense = df[df["Amount"] < 0]["Amount"].sum()
        net_cash = income + expense

        st.write(f"🟢 Income: ${income:,.2f}")
        st.write(f"🔴 Expenses: ${expense:,.2f}")
        st.write(f"💰 Net Cash Flow: ${net_cash:,.2f}")

        st.info("This is a basic MVP. Add OpenAI next for full AI insights.")

st.markdown("---")
st.caption("FundSight | AI-Driven Forecasting for Nonprofits")
