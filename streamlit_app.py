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

# --- PAGE CONFIG ---
st.set_page_config(page_title="FundSight: Nonprofit Finance Dashboard", page_icon="📊", layout="wide")

# --- LOGO & WELCOME BANNER ---
st.image("fundsight_logo.png", width=200)
st.markdown("## 👋 Welcome to FundSight – Built for Nonprofit Finance Teams")

# --- CLIENT SELECTION ---
st.sidebar.header("👥 Client Selection")
client_names = ["Client A", "Client B", "Client C"]
selected_client = st.sidebar.selectbox("Select Client", client_names)

# --- FILE UPLOADS ---
st.sidebar.markdown(f"### Upload files for {selected_client}")
uploaded_file = st.sidebar.file_uploader("Upload QuickBooks CSV", type=["csv"], key=f"{selected_client}_qb")
budget_file = st.sidebar.file_uploader("Upload Budget CSV (optional)", type=["csv"], key=f"{selected_client}_budget")
mortgage_file = st.sidebar.file_uploader("Upload Mortgage CSV", type=["csv"], key=f"{selected_client}_mortgage")

# --- MAIN DASHBOARD ---
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Account"] = df["Account"].str.strip()
    df["Name"] = df.get("Name", "Unknown")

    income = df[df["Amount"] > 0]["Amount"].sum()
    expenses = df[df["Amount"] < 0]["Amount"].sum()
    net = income + expenses
    cash_on_hand = df["Amount"].sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("🟢 Total Income", f"${income:,.2f}")
    col2.metric("🔴 Total Expenses", f"${expenses:,.2f}")
    col3.metric("💰 Net Cash Flow", f"${net:,.2f}")
    st.markdown("---")

    # Daily Cash Flow Trend
    st.subheader("📈 Daily Cash Flow Trend")
    daily_totals = df.groupby("Date")["Amount"].sum().reset_index()
    fig1, ax1 = plt.subplots()
    ax1.plot(daily_totals["Date"], daily_totals["Amount"])
    st.pyplot(fig1)

    # Expenses by Category
    st.subheader("📊 Expenses by Account Category")
    expense_df = df[df["Amount"] < 0]
    by_category = expense_df.groupby("Account")["Amount"].sum().sort_values()
    fig2, ax2 = plt.subplots()
    by_category.abs().plot(kind='barh', ax=ax2)
    st.pyplot(fig2)

    # Budget vs Actuals
    if budget_file is not None:
        st.subheader("📋 Budget vs Actuals")
        budget_df = pd.read_csv(budget_file)
        actuals = df.groupby("Account")["Amount"].sum()
        comparison = pd.merge(budget_df, actuals.rename("Actual"), on="Account", how="outer").fillna(0)
        comparison["Variance"] = comparison["Actual"] - comparison["Budget Amount"]
        st.dataframe(comparison)

    # Mortgage Module
    if mortgage_file is not None:
        st.subheader("🏠 Mortgage Tracker")
        mortgage_df = pd.read_csv(mortgage_file)
        if "Amount Due" in mortgage_df.columns and "Amount Paid" in mortgage_df.columns:
            mortgage_df["Balance"] = mortgage_df["Amount Due"] - mortgage_df["Amount Paid"]
            mortgage_df["Delinquent"] = mortgage_df["Balance"] > 0
            delinquent_count = mortgage_df["Delinquent"].sum()
            st.metric("🚨 Delinquent Loans", int(delinquent_count))
            st.dataframe(mortgage_df)

    # PDF Report + Email to Board
    st.subheader("📤 Send Board Report")
    board_email = st.text_input("Board Email Address", "jacob.b.franco@gmail.com")
    if st.button("Send Monthly Board Report"):
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, f"FundSight Board Report – {selected_client}", ln=True)
            pdf.ln(10)
            summary = (
                f"Total Income: ${income:,.2f}\n"
                f"Total Expenses: ${expenses:,.2f}\n"
                f"Net Cash Flow: ${net:,.2f}\n"
                f"Cash on Hand: ${cash_on_hand:,.2f}"
            )
            for line in summary.split("\n"):
                pdf.multi_cell(0, 10, line)
            pdf_path = "/tmp/fundsight_board_report.pdf"
            pdf.output(pdf_path)

            msg = MIMEMultipart()
            msg["From"] = st.secrets["email_user"]
            msg["To"] = board_email
            msg["Subject"] = f"Board Report – {selected_client}"
            body = f"Attached is this month's board report for {selected_client}.\n\n-FundSight"
            msg.attach(MIMEText(body, "plain"))
            with open(pdf_path, "rb") as f:
                msg.attach(MIMEApplication(f.read(), _subtype="pdf", name="Board_Report.pdf"))
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(st.secrets["email_user"], st.secrets["email_password"])
            server.sendmail(msg["From"], msg["To"], msg.as_string())
            server.quit()
            st.success("✅ Board Report sent successfully!")
        except Exception as e:
            st.error(f"❌ Error: {e}")
else:
    st.info("📤 Please upload a QuickBooks CSV file to begin.")

# Footer
st.markdown("---")
st.markdown("FundSight © 2025 | Built for Nonprofits")


