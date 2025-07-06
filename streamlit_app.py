import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from fpdf import FPDF
import os

# --- APP CONFIG ---
st.set_page_config(page_title="FundSight: Nonprofit Finance Dashboard", page_icon="📊", layout="wide")
st.image("fundsight_logo.png", width=200)
st.markdown("<h2 style='text-align: center;'>Welcome to FundSight – Built for Nonprofit Financial Clarity</h2>", unsafe_allow_html=True)
st.markdown("---")

# --- CLIENT SELECTION ---
st.sidebar.header("👥 Client Selection")
client_names = ["Habitat for Humanity", "Client B", "Client C"]
selected_client = st.sidebar.selectbox("Select Client", client_names)

# --- FILE UPLOADS ---
st.sidebar.subheader(f"Upload QuickBooks + Optional Files for {selected_client}")
uploaded_file = st.sidebar.file_uploader("Upload QuickBooks CSV", type=["csv"], key=f"{selected_client}_qb")
budget_file = st.sidebar.file_uploader("Upload Budget CSV (optional)", type=["csv"], key=f"{selected_client}_budget")
mortgage_file = st.sidebar.file_uploader("Upload Mortgage CSV (optional)", type=["csv"], key=f"{selected_client}_mortgage")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Account"] = df["Account"].str.strip()
    df["Name"] = df.get("Name", pd.Series(["Unknown"] * len(df))).fillna("Unknown")

    income = df[df["Amount"] > 0]["Amount"].sum()
    expenses = df[df["Amount"] < 0]["Amount"].sum()
    net = income + expenses
    cash_on_hand = df["Amount"].sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("🟢 Total Income", f"${income:,.2f}")
    col2.metric("🔴 Total Expenses", f"${expenses:,.2f}")
    col3.metric("💰 Net Cash Flow", f"${net:,.2f}")
    st.markdown("---")

    # Daily Cash Flow
    st.subheader("📈 Daily Cash Flow Trend")
    daily_totals = df.groupby("Date")["Amount"].sum().reset_index()
    fig1, ax1 = plt.subplots()
    ax1.plot(daily_totals["Date"], daily_totals["Amount"])
    ax1.set_title("Daily Cash Flow")
    ax1.tick_params(axis='x', rotation=45)
    st.pyplot(fig1)

    # Expenses by Category
    st.subheader("📊 Expenses by Account Category")
    expense_df = df[df["Amount"] < 0]
    by_category = expense_df.groupby("Account")["Amount"].sum().sort_values()
    fig2, ax2 = plt.subplots()
    by_category.abs().plot(kind='barh', ax=ax2)
    ax2.set_title("Expenses by Category")
    st.pyplot(fig2)

    # Pie Chart
    st.subheader("🧁 Expense Distribution")
    fig3, ax3 = plt.subplots()
    ax3.pie(by_category.abs(), labels=by_category.index, autopct="%1.1f%%", startangle=90)
    ax3.axis("equal")
    st.pyplot(fig3)

    # Forecast
    st.subheader("📅 30-Day Cash Flow Projection")
    daily_avg = daily_totals["Amount"].mean()
    forecast_df = pd.DataFrame({
        "Date": pd.date_range(daily_totals["Date"].max() + timedelta(days=1), periods=30),
        "Amount": daily_avg
    })
    fig4, ax4 = plt.subplots()
    ax4.plot(forecast_df["Date"], forecast_df["Amount"])
    ax4.set_title("30-Day Forecast")
    st.pyplot(fig4)

    # Budget vs Actuals
    if budget_file is not None:
        st.subheader("📋 Budget vs Actuals")
        budget_df = pd.read_csv(budget_file)
        budget_df.columns = budget_df.columns.str.strip()
        budget_df["Account"] = budget_df["Account"].str.strip()
        if {"Account", "Budget Amount"}.issubset(budget_df.columns):
            actuals = df.groupby("Account")["Amount"].sum()
            comparison = pd.merge(budget_df, actuals.rename("Actual"), on="Account", how="outer").fillna(0)
            comparison["Variance"] = comparison["Actual"] - comparison["Budget Amount"]
            comparison["Variance %"] = (comparison["Variance"] / budget_df["Budget Amount"].replace(0, 1)) * 100
            st.dataframe(comparison)

    # Mortgage Tracking
    if mortgage_file:
        st.subheader("🏠 Mortgage Tracking Module")
        mortgage_df = pd.read_csv(mortgage_file)
        if {"Borrower", "Loan ID", "Amount Due", "Amount Paid", "Due Date"}.issubset(mortgage_df.columns):
            mortgage_df["Due Date"] = pd.to_datetime(mortgage_df["Due Date"])
            mortgage_df["Balance"] = mortgage_df["Amount Due"] - mortgage_df["Amount Paid"]
            mortgage_df["Delinquent"] = mortgage_df["Due Date"] < pd.Timestamp.today() - timedelta(days=60)

            st.metric("Total Balance Due", f"${mortgage_df['Balance'].sum():,.2f}")
            st.metric("Delinquent Loans", mortgage_df["Delinquent"].sum())

            st.markdown("### 🔎 Mortgage Status Breakdown")
            fig5, ax5 = plt.subplots()
            mortgage_df["Delinquent Label"] = mortgage_df["Delinquent"].map({True: "Delinquent", False: "Current"})
            mortgage_df.groupby("Delinquent Label")["Balance"].sum().plot(kind='pie', autopct="%1.1f%%", ax=ax5)
            ax5.set_ylabel("")
            st.pyplot(fig5)

            st.dataframe(mortgage_df)

    # Email Board Report (simplified preview)
    st.subheader("📩 Board Report Generator")
    board_email = st.text_input("Enter Board Member Email", value="jacob.b.franco@gmail.com")
    if st.button("Send Board Report PDF"):
        st.success(f"✅ Board Report successfully sent to {board_email} (demo mode)")

else:
    st.info("📤 Please upload a QuickBooks CSV to begin.")




