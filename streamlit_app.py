import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

st.title("Test Dashboard for QuickBooks Data")

uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.write("Raw data loaded (rows):", len(df))
    st.write("Columns:", df.columns.tolist())
    
    df["Date"] = pd.to_datetime(df["Date"])
    df["Account"] = df["Account"].str.strip()  # <-- fixes hidden chart bugs

    income = df[df["Amount"] > 0]["Amount"].sum()
    expenses = df[df["Amount"] < 0]["Amount"].sum()
    net = income + expenses

    st.metric("🟢 Income", f"${income:,.2f}")
    st.metric("🔴 Expenses", f"${expenses:,.2f}")
    st.metric("💰 Net Cash Flow", f"${net:,.2f}")

    # Daily cash flow line chart
    daily_totals = df.groupby("Date")["Amount"].sum().reset_index()
    st.write("Daily totals preview (full):", daily_totals)
    st.write("Daily totals dtypes:", daily_totals.dtypes)
    st.write("Daily totals nulls:", daily_totals.isnull().sum())
    st.line_chart(daily_totals.set_index("Date"))

    # Expenses by category bar chart
    expense_df = df[df["Amount"] < 0]
    by_category = expense_df.groupby("Account")["Amount"].sum()
    st.write("By category preview (full):", by_category)
    st.write("By category dtype:", by_category.dtype)
    st.write("By category nulls:", by_category.isnull().sum())
    st.bar_chart(by_category.abs())

    # Pie chart for expenses
    fig, ax = plt.subplots()
    ax.pie(by_category.abs(), labels=by_category.index, autopct="%1.1f%%")
    st.pyplot(fig)

    # Dummy charts to verify Streamlit plotting works
    st.write("Dummy line chart test")
    st.line_chart(pd.DataFrame({"x": range(10), "y": np.random.randn(10)}).set_index("x"))
    st.write("Dummy bar chart test")
    st.bar_chart(pd.Series([5, 3, 6, 2], index=["A", "B", "C", "D"]))
