import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.title("Test Dashboard for QuickBooks Data")

uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df["Date"] = pd.to_datetime(df["Date"])

    income = df[df["Amount"] > 0]["Amount"].sum()
    expenses = df[df["Amount"] < 0]["Amount"].sum()
    net = income + expenses

    st.metric("🟢 Income", f"${income:,.2f}")
    st.metric("🔴 Expenses", f"${expenses:,.2f}")
    st.metric("💰 Net Cash Flow", f"${net:,.2f}")

    # Daily cash flow line chart
    daily_totals = df.groupby("Date")["Amount"].sum().reset_index()
    st.line_chart(daily_totals.set_index("Date"))

    # Expenses by category bar chart
    expense_df = df[df["Amount"] < 0]
    by_category = expense_df.groupby("Account")["Amount"].sum()
    st.bar_chart(by_category.abs())

    # Pie chart for expenses
    fig, ax = plt.subplots()
    ax.pie(by_category.abs(), labels=by_category.index, autopct="%1.1f%%")
    st.pyplot(fig)







           
