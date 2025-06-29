import streamlit as st
import pandas as pd

st.title("Minimal Chart Test")

data = {
    "Date": pd.date_range(start="2025-06-01", periods=5),
    "Amount": [100, -50, 200, -150, 50],
    "Account": ["Sales", "Rent", "Sales", "Rent", "Sales"]
}
df = pd.DataFrame(data)
st.write(df)

daily_totals = df.groupby("Date")["Amount"].sum().reset_index()
st.line_chart(daily_totals.set_index("Date"))

expense_df = df[df["Amount"] < 0]
by_category = expense_df.groupby("Account")["Amount"].sum()
st.bar_chart(by_category.abs())
