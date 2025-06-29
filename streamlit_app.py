import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import timedelta

st.set_page_config(page_title="FundSight: Nonprofit Finance Dashboard", layout="wide")
st.title("📊 FundSight: QuickBooks Dashboard for Nonprofits")

# Uploads
uploaded_file = st.file_uploader("Upload your QuickBooks CSV", type=["csv"])
budget_file = st.file_uploader("Upload your Budget CSV (optional)", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Account"] = df["Account"].str.strip()
    if "Name" in df.columns:
        df["Name"] = df["Name"].fillna("Unknown")

    # Summary metrics
    income = df[df["Amount"] > 0]["Amount"].sum()
    expenses = df[df["Amount"] < 0]["Amount"].sum()
    net = income + expenses
    col1, col2, col3 = st.columns(3)
    col1.metric("🟢 Total Income", f"${income:,.2f}")
    col2.metric("🔴 Total Expenses", f"${expenses:,.2f}")
    col3.metric("💰 Net Cash Flow", f"${net:,.2f}")

    st.markdown("---")

    # Daily Cash Flow Trend
    st.subheader("📈 Daily Cash Flow Trend")
    daily_totals = df.groupby("Date")["Amount"].sum().reset_index()
    st.line_chart(daily_totals.set_index("Date"))

    # Expense by Account
    st.subheader("📊 Expenses by Account Category")
    expense_df = df[df["Amount"] < 0]
    by_category = expense_df.groupby("Account")["Amount"].sum().sort_values()
    st.bar_chart(by_category.abs())

    # Expense Pie Chart
    st.subheader("🧁 Expense Distribution")
    fig, ax = plt.subplots()
    ax.pie(by_category.abs(), labels=by_category.index, autopct="%1.1f%%", startangle=90)
    ax.axis("equal")
    st.pyplot(fig)

    # 30-Day Forecast
    st.subheader("📅 30-Day Cash Flow Projection")
    daily_avg = daily_totals["Amount"].mean()
    future_dates = pd.date_range(start=daily_totals["Date"].max() + timedelta(days=1), periods=30)
    forecast_df = pd.DataFrame({"Date": future_dates, "Amount": daily_avg})
    st.line_chart(forecast_df.set_index("Date"))

    st.markdown("---")

    # 📋 Budget vs Actuals
    if budget_file:
        st.subheader("📋 Budget vs Actuals")
        budget_df = pd.read_csv(budget_file)
        budget_df.columns = budget_df.columns.str.strip()
        budget_df["Account"] = budget_df["Account"].str.strip()

        if {"Account", "Budget Amount"}.issubset(budget_df.columns):
            actuals = df.groupby("Account")["Amount"].sum()
            comparison = pd.merge(
                budget_df,
                actuals.rename("Actual"),
                on="Account",
                how="outer"
            ).fillna(0)
            comparison["Variance"] = comparison["Actual"] - comparison["Budget Amount"]
            comparison["Variance %"] = (comparison["Variance"] / comparison["Budget Amount"].replace(0, 1)) * 100

            st.dataframe(comparison)
            st.bar_chart(comparison.set_index("Account")[["Budget Amount", "Actual"]].abs())
        else:
            st.warning("Budget file must include 'Account' and 'Budget Amount' columns.")

    st.markdown("---")

    # 📊 Trend Analysis & Seasonality
    st.subheader("📉 Trend Analysis")
    monthly_trend = df.groupby(df["Date"].dt.to_period("M"))["Amount"].sum().reset_index()
    monthly_trend["Date"] = monthly_trend["Date"].astype(str)
    st.line_chart(monthly_trend.set_index("Date"))

    # 💸 Donor or Revenue Source Breakdown
    if "Name" in df.columns:
        st.subheader("💌 Top Revenue Sources")
        top_sources = df[df["Amount"] > 0].groupby("Name")["Amount"].sum().sort_values(ascending=False).head(10)
        st.bar_chart(top_sources)

    # 🔍 Expense Breakdown by Month
    st.subheader("🔍 Monthly Expense Drill-down")
    expense_by_month = expense_df.groupby([df["Date"].dt.to_period("M"), "Account"])["Amount"].sum().unstack().fillna(0)
    st.line_chart(expense_by_month.abs())

    # 📈 Financial KPIs
    st.subheader("📊 Key Financial Ratios")
    cash_on_hand = df["Amount"].sum()
    monthly_expense_avg = abs(expense_df["Amount"].resample("M", on="Date").sum().mean())
    kpis = {
        "💵 Days Cash on Hand": (cash_on_hand / monthly_expense_avg * 30) if monthly_expense_avg else 0,
        "📊 Program Expense Ratio": abs(expense_df["Amount"].sum()) / abs(df["Amount"].sum()) if not df.empty else 0,
    }
    for label, value in kpis.items():
        st.metric(label, f"{value:,.1f}" if "Ratio" not in label else f"{value:.2%}")

    # 🔔 Alerts
    st.subheader("🔔 Alerts")
    cash_threshold = st.number_input("Set Minimum Cash Threshold", value=5000)
    if cash_on_hand < cash_threshold:
        st.error(f"⚠️ Alert: Cash on hand is below threshold (${cash_threshold})")
    else:
        st.success(f"✅ Cash on hand is above the safe threshold.")

    # 🔄 Scenario Modeling
    st.subheader("🔄 Scenario Modeling")
    donation_increase = st.slider("Increase Donations by (%)", -50, 100, 0)
    expense_reduction = st.slider("Reduce Expenses by (%)", 0, 50, 0)

    scenario_income = income * (1 + donation_increase / 100)
    scenario_expense = expenses * (1 - expense_reduction / 100)
    scenario_net = scenario_income + scenario_expense

    st.write(f"📈 Scenario Net Cash Flow: ${scenario_net:,.2f}")

    # 📆 Multi-Year Comparison
    st.subheader("📆 Multi-Year Comparison")
    if df["Date"].dt.year.nunique() > 1:
        multi_year = df.groupby(df["Date"].dt.year)["Amount"].sum()
        st.bar_chart(multi_year)

    # 📁 Download Report
    st.subheader("📥 Downloadable Report")
    report = df.copy()
    report["Year"] = report["Date"].dt.year
    csv = report.to_csv(index=False)
    st.download_button("Download Full Data CSV", csv, "fundsight_report.csv", "text/csv")

else:
    st.info("📤 Please upload a QuickBooks CSV file to get started.")
