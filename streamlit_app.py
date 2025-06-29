import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="FundSight: Nonprofit Finance Dashboard", layout="wide")

st.title("📊 FundSight: QuickBooks Dashboard for Nonprofits")

uploaded_file = st.file_uploader("Upload your QuickBooks CSV", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # Clean and prepare data
    df["Date"] = pd.to_datetime(df["Date"])
    df["Account"] = df["Account"].str.strip()
    
    # Basic financial metrics
    income = df[df["Amount"] > 0]["Amount"].sum()
    expenses = df[df["Amount"] < 0]["Amount"].sum()
    net = income + expenses

    col1, col2, col3 = st.columns(3)
    col1.metric("🟢 Total Income", f"${income:,.2f}")
    col2.metric("🔴 Total Expenses", f"${expenses:,.2f}")
    col3.metric("💰 Net Cash Flow", f"${net:,.2f}")

    st.markdown("---")

    # Line chart: Daily cash flow
    st.subheader("📈 Daily Cash Flow")
    daily_totals = df.groupby("Date")["Amount"].sum().reset_index()
    st.line_chart(daily_totals.set_index("Date"))

    # Bar chart: Expenses by category
    st.subheader("📊 Expenses by Account Category")
    expense_df = df[df["Amount"] < 0]
    by_category = expense_df.groupby("Account")["Amount"].sum().sort_values()
    st.bar_chart(by_category.abs())

    # Pie chart: Expenses breakdown
    st.subheader("🧁 Expense Distribution (Pie Chart)")
    fig, ax = plt.subplots()
    ax.pie(by_category.abs(), labels=by_category.index, autopct="%1.1f%%", startangle=90)
    ax.axis("equal")
    st.pyplot(fig)

else:
    st.info("📤 Please upload a QuickBooks CSV file to get started.")
