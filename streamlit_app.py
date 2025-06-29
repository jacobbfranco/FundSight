import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import datetime as dt

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

    # PHASE 1: CASH FLOW FORECAST
    st.subheader("📉 Cash Flow Forecast (Next 3 Months)")

    df["Month"] = df["Date"].dt.to_period("M")
    monthly = df.groupby("Month")["Amount"].sum().reset_index()
    monthly["Month"] = monthly["Month"].dt.to_timestamp()

    # Use rolling average to forecast
    lookback_months = 3
    avg_income = df[df["Amount"] > 0].groupby("Month")["Amount"].sum().rolling(lookback_months).mean().iloc[-1]
    avg_expense = df[df["Amount"] < 0].groupby("Month")["Amount"].sum().rolling(lookback_months).mean().iloc[-1]

    future_months = pd.date_range(start=monthly["Month"].max() + pd.offsets.MonthBegin(), periods=3, freq='MS')
    forecast_df = pd.DataFrame({
        "Month": future_months,
        "Forecast Income": avg_income,
        "Forecast Expenses": avg_expense,
        "Forecast Net": avg_income + avg_expense
    })

    monthly["Forecast Income"] = np.nan
    monthly["Forecast Expenses"] = np.nan
    monthly["Forecast Net"] = monthly["Amount"]
    forecast_combined = pd.concat([
        monthly[["Month", "Forecast Income", "Forecast Expenses", "Forecast Net"]],
        forecast_df
    ])

    st.line_chart(forecast_combined.set_index("Month")[["Forecast Net"]])

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
