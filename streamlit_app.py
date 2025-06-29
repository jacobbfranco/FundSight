import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import timedelta

# Set page config
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

    st.markdown("---")

    # 🔮 Forecast: Simple 30-day projection
    st.subheader("📅 30-Day Cash Flow Forecast")
    df = df.sort_values("Date")
    recent = df[df["Date"] >= df["Date"].max() - pd.Timedelta(days=30)]
    avg_daily = recent.groupby("Date")["Amount"].sum().mean()

    forecast_days = 30
    forecast_dates = pd.date_range(start=df["Date"].max() + timedelta(days=1), periods=forecast_days)
    forecast_values = [avg_daily] * forecast_days
    forecast_df = pd.DataFrame({"Date": forecast_dates, "Forecasted Cash Flow": forecast_values})

    st.line_chart(forecast_df.set_index("Date"))

    st.caption(f"Based on average daily cash flow over the last 30 days: ${avg_daily:,.2f}/day")

else:
    st.info("📤 Please upload a QuickBooks CSV file to get started.")
