import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import timedelta

st.set_page_config(page_title="FundSight: Nonprofit Finance Dashboard", layout="wide")
st.title("📊 FundSight: QuickBooks Dashboard for Nonprofits")

uploaded_file = st.file_uploader("Upload your QuickBooks CSV", type=["csv"])
budget_file = st.file_uploader("Upload your Budget CSV (optional)", type=["csv"])

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

    # 🔮 Forecast: 30-Day Cash Flow Projection
    st.subheader("📅 Projected 30-Day Cash Flow")
    daily_avg = daily_totals["Amount"].mean()
    last_date = daily_totals["Date"].max()
    future_dates = pd.date_range(start=last_date + timedelta(days=1), periods=30)
    forecast_df = pd.DataFrame({"Date": future_dates, "Amount": daily_avg})
    st.line_chart(forecast_df.set_index("Date"))

    st.markdown("---")

    # 📋 Budget vs Actuals
    if budget_file:
        st.subheader("📋 Budget vs Actuals Comparison")

        budget_df = pd.read_csv(budget_file)
        budget_df.columns = budget_df.columns.str.strip()
        budget_df["Account"] = budget_df["Account"].str.strip()

        required_columns = {"Account", "Budget Amount"}
        if not required_columns.issubset(set(budget_df.columns)):
            st.error(f"⚠️ Your budget file is missing required columns: {required_columns}")
        else:
            actuals = df.groupby("Account")["Amount"].sum()
            comparison = pd.merge(
                budget_df,
                actuals.rename("Actual"),
                on="Account",
                how="outer"
            ).fillna(0)

            comparison["Variance"] = comparison["Actual"] - comparison["Budget Amount"]
            comparison["Variance %"] = (comparison["Variance"] / comparison["Budget Amount"].replace(0, 1)) * 100

            st.dataframe(
                comparison.style.format({
                    "Budget Amount": "${:,.2f}",
                    "Actual": "${:,.2f}",
                    "Variance": "${:,.2f}",
                    "Variance %": "{:+.1f}%"
                }).applymap(
                    lambda v: 'color: red;' if isinstance(v, (int, float)) and v < 0 else 'color: green;',
                    subset=["Variance"]
                )
            )

            st.bar_chart(comparison.set_index("Account")[["Budget Amount", "Actual"]].abs())

else:
    st.info("📤 Please upload a QuickBooks CSV file to get started.")
