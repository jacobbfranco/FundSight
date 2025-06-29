import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="FundSight AI", layout="wide")
st.title("Nonprofit Finance Insights")

uploaded_file = st.file_uploader("Upload QuickBooks CSV Export", type=["csv"])
if uploaded_file:
    df = pd.read_csv(uploaded_file)

    st.subheader("📄 Data Preview")
    st.dataframe(df.head())

    # Convert date column
    df["Date"] = pd.to_datetime(df["Date"])

    # Summary stats
    st.header("📊 Financial Dashboard")
    income = df[df["Amount"] > 0]["Amount"].sum()
    expenses = df[df["Amount"] < 0]["Amount"].sum()
    net = income + expenses

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Income", f"${income:,.2f}")
    col2.metric("Total Expenses", f"${expenses:,.2f}")
    col3.metric("Net Cash Flow", f"${net:,.2f}")

    # Daily cash flow chart
    daily_totals = df.groupby("Date")["Amount"].sum().reset_index()
    st.subheader("💹 Daily Cash Flow")
    st.line_chart(daily_totals.set_index("Date"))

    # Expense breakdown
    expense_df = df[df["Amount"] < 0]
    by_category = expense_df.groupby("Account")["Amount"].sum().sort_values()

    st.subheader("📉 Expenses by Category")
    st.bar_chart(by_category.abs())

    # Pie chart of expenses
    st.subheader("📌 Pie Chart of Expenses")
    fig, ax = plt.subplots()
    ax.pie(by_category.abs(), labels=by_category.index, autopct="%1.1f%%")
    st.pyplot(fig)

    # Filter by account
    st.subheader("🔍 Filter Data")
    accounts = df["Account"].unique()
    selected_accounts = st.multiselect("Filter by Account", accounts, default=list(accounts))
    filtered_df = df[df["Account"].isin(selected_accounts)]
    st.dataframe(filtered_df)

st.markdown("---")
st.caption("FundSight | AI-Driven Forecasting







           
