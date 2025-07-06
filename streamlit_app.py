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

st.set_page_config(page_title="FundSight: Nonprofit Finance Dashboard", layout="wide")
st.title("📊 FundSight: QuickBooks Dashboard for Nonprofits")

# --- MULTI-CLIENT SELECTION ---
st.sidebar.header("👥 Client Selection")
client_names = ["Habitat for Humanity"]
selected_client = st.sidebar.selectbox("Select Client", client_names)

# --- FILE UPLOADS ---
st.sidebar.markdown(f"### Upload files for {selected_client}")
uploaded_file = st.sidebar.file_uploader("Upload QuickBooks CSV", type=["csv"], key=f"{selected_client}_qb")
budget_file = st.sidebar.file_uploader("Upload Budget CSV (optional)", type=["csv"], key=f"{selected_client}_budget")
mortgage_file = st.sidebar.file_uploader("Upload Mortgage CSV", type=["csv"], key=f"{selected_client}_mortgage")

# Optional Modules
st.sidebar.markdown("### Optional Modules")
show_mortgage = st.sidebar.checkbox("📋 Include Mortgage Tracking")
show_board_report = st.sidebar.checkbox("📩 Include Board Report Generator")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Account"] = df["Account"].str.strip()
    if "Name" in df.columns:
        df["Name"] = df["Name"].fillna("Unknown")

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
    fig1.tight_layout()
    st.pyplot(fig1)

    # Expenses by Category
    st.subheader("📊 Expenses by Account Category")
    expense_df = df[df["Amount"] < 0]
    by_category = expense_df.groupby("Account")["Amount"].sum().sort_values()
    fig2, ax2 = plt.subplots()
    by_category.abs().plot(kind='barh', ax=ax2)
    ax2.set_title("Expenses by Category")
    fig2.tight_layout()
    st.pyplot(fig2)

    # Pie Chart
    st.subheader("🧁 Expense Distribution")
    fig3, ax3 = plt.subplots()
    ax3.pie(by_category.abs(), labels=by_category.index, autopct="%1.1f%%", startangle=90)
    ax3.axis("equal")
    st.pyplot(fig3)

    # 30-Day Forecast
    st.subheader("📅 30-Day Cash Flow Projection")
    daily_avg = daily_totals["Amount"].mean()
    forecast_df = pd.DataFrame({
        "Date": pd.date_range(daily_totals["Date"].max() + timedelta(days=1), periods=30),
        "Amount": daily_avg
    })
    fig4, ax4 = plt.subplots()
    ax4.plot(forecast_df["Date"], forecast_df["Amount"])
    ax4.set_title("30-Day Forecast")
    fig4.tight_layout()
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

    # --- Mortgage Tracking Module ---
    if show_mortgage and mortgage_file:
        st.subheader("🏠 Mortgage Tracking Module")
        st.markdown("Upload your mortgage CSV file (Borrower, Loan ID, Amount Due, Amount Paid, Due Date)")
        mortgage_df = pd.read_csv(mortgage_file)
        st.dataframe(mortgage_df.head())

        if {"Amount Due", "Amount Paid"}.issubset(mortgage_df.columns):
            mortgage_df["Balance"] = mortgage_df["Amount Due"] - mortgage_df["Amount Paid"]
            st.line_chart(mortgage_df.set_index("Loan ID")["Balance"])

        if "Delinquent" in mortgage_df.columns:
            st.metric("🚨 Delinquent Loans", int(mortgage_df["Delinquent"].sum()))

    # --- Board Report Module ---
    if show_board_report:
        st.subheader("📋 Board Reports")
        board_email = st.text_input("📧 Board Email Address", "jacob.b.franco@gmail.com")
        if st.button("Send Monthly Board Report"):
            try:
                msg = MIMEMultipart()
                msg["From"] = st.secrets["email_user"]
                msg["To"] = board_email
                msg["Subject"] = f"Monthly Board Report – {selected_client}"
                summary = f'''
Dear Board Member,

Attached is this month's FundSight financial overview for {selected_client}.

• Total Income: ${income:,.2f}
• Total Expenses: ${expenses:,.2f}
• Net Cash Flow: ${net:,.2f}
• Days Cash on Hand: {(cash_on_hand / (abs(expenses) / 30)) if expenses else 0:.1f}

Warm regards,
FundSight Board Reporting Tool
'''
                msg.attach(MIMEText(summary, "plain"))
                st.success("✅ Board Report sent successfully! (mocked)")

            except Exception as e:
                st.error(f"❌ Error sending board report: {e}")


