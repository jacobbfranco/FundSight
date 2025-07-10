import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
import os

# --- Config ---
st.set_page_config(page_title="FundSight Dashboard", layout="wide", page_icon="📊")

# --- Header ---
st.image("fundsight_logo.png", width=150)
st.markdown("""
    <h1 style='text-align: center;'>📊 FundSight Dashboard</h1>
    <h4 style='text-align: center; color: gray;'>Built for Habitat for Humanity Affiliates</h4>
    <hr style='margin-top:10px; margin-bottom:30px;'>
""", unsafe_allow_html=True)

# --- Sidebar ---
client_names = ["Client A", "Client B", "Client C"]
selected_client = st.sidebar.selectbox("Select Client", client_names)

st.sidebar.markdown("### 📂 Upload Files")
uploaded_file = st.sidebar.file_uploader("Upload QuickBooks CSV", type=["csv"])
budget_file = st.sidebar.file_uploader("Upload Budget CSV (optional)", type=["csv"])
tag_file = st.sidebar.file_uploader("Upload Tag CSV (optional)", type=["csv"])
mortgage_file = st.sidebar.file_uploader("Upload Mortgage CSV (optional)", type=["csv"])

st.sidebar.markdown("### ⚙️ Options")
show_mortgages = st.sidebar.checkbox("Show Mortgage Module", value=True)
show_board = st.sidebar.checkbox("Show Board Reporting", value=True)

# --- Format Helper ---
def format_currency(value):
    return f"${value:,.2f}" if value >= 0 else f"(${abs(value):,.2f})"

def section_divider():
    st.markdown("<hr style='margin:20px 0;'>", unsafe_allow_html=True)

# --- Main Dashboard ---
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
    df = df.dropna(subset=["Date"])

    # Tags (optional)
    tags = {}
    if tag_file:
        try:
            tag_df = pd.read_csv(tag_file)
            tags = dict(zip(tag_df["Transaction"], tag_df["Tag"]))
        except:
            st.warning("Tag file format issue.")

    # Metrics
    income = df[df["Amount"] > 0]["Amount"].sum()
    expenses = df[df["Amount"] < 0]["Amount"].sum()
    net_cash = income + expenses

    col1, col2, col3 = st.columns(3)
    col1.metric("🟢 Total Income", format_currency(income))
    col2.metric("🔴 Total Expenses", format_currency(expenses))
    col3.metric("💰 Net Cash Flow", format_currency(net_cash))

    section_divider()

    # Forecast
    st.subheader("📈 30-Day Forecast")
    forecast = df.groupby(df["Date"].dt.date)["Amount"].sum().reset_index()
    forecast = forecast.rename(columns={"Date": "Day"})
    forecast["Day"] = pd.to_datetime(forecast["Day"])
    forecast = forecast.set_index("Day").resample("D").sum().fillna(0).cumsum()

    fig, ax = plt.subplots()
    ax.plot(forecast.index, forecast["Amount"], linewidth=2)
    st.pyplot(fig)

    section_divider()

    # Expenses by Category
    st.subheader("📊 Expenses by Category")
    if "Category" in df.columns:
        chart = df[df["Amount"] < 0].groupby("Category")["Amount"].sum().sort_values()
        st.bar_chart(chart.abs())
    else:
        st.warning("No 'Category' column found.")

    section_divider()

    # Budget vs Actuals
    st.subheader("📊 Budget vs Actuals")
    if budget_file:
        try:
            bdf = pd.read_csv(budget_file)
            if "Category" in bdf.columns and "Budget" in bdf.columns:
                actuals = df[df["Amount"] < 0].groupby("Category")["Amount"].sum().abs()
                merged = bdf.set_index("Category").join(actuals.rename("Actual"), how="left").fillna(0)
                merged["Variance"] = merged["Budget"] - merged["Actual"]
                st.dataframe(merged.style.format("${:,.2f}"))
            else:
                st.warning("Missing required columns in budget file.")
        except:
            st.warning("Issue reading budget file.")

    section_divider()

    # Financial Ratios
    st.subheader("📊 Financial Ratios")
    if expenses:
        st.markdown(f"**Savings Ratio:** {((income - abs(expenses)) / abs(expenses)):.2f}")
        st.markdown(f"**Burn Rate (Monthly):** {abs(expenses / 30):,.2f}")

    section_divider()

    # Alerts
    st.subheader("🚨 Alerts")
    cash_threshold = st.sidebar.number_input("Low Cash Warning Threshold", value=5000)
    if net_cash < cash_threshold:
        st.error(f"⚠️ Net cash is below threshold: {format_currency(net_cash)}")

    large_limit = st.sidebar.number_input("High Expense Alert", value=10000)
    large_expenses = df[df["Amount"] < -large_limit]
    if not large_expenses.empty:
        st.warning("⚠️ High expenses detected:")
        show_cols = [col for col in ["Date", "Description", "Amount"] if col in df.columns]
        st.dataframe(large_expenses[show_cols])

    section_divider()

    # Add-on: Mortgage
    if show_mortgages and mortgage_file:
        st.subheader("🏠 Mortgage Tracking")
        try:
            mdf = pd.read_csv(mortgage_file)
            if {"Homeowner", "Loan Amount", "Remaining Balance", "Delinquent"}.issubset(mdf.columns):
                st.metric("Total Loans", format_currency(mdf["Loan Amount"].sum()))
                st.metric("Remaining Balance", format_currency(mdf["Remaining Balance"].sum()))
                st.metric("Delinquent Accounts", int((mdf["Delinquent"] > 0).sum()))
                st.dataframe(mdf)
            else:
                st.warning("Required mortgage columns not found.")
        except:
            st.warning("Error loading mortgage file.")

    section_divider()

    # Scenario Modeling
    st.subheader("🔮 Scenario Modeling")
    sim_income = st.number_input("Projected Income", value=float(income))
    sim_expense = st.number_input("Projected Expenses", value=float(abs(expenses)))
    st.success(f"Projected Net: {format_currency(sim_income - sim_expense)}")

    section_divider()

    # Board Notes
    if show_board:
        st.subheader("📝 Board Notes")
        board_notes = st.text_area("Notes for Board Report")

    section_divider()

    # PDF Download
    st.subheader("📥 Generate PDF Report")
    if st.button("Generate PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(200, 10, txt=f"FundSight Report - {selected_client}", ln=1, align="C")
        pdf.set_font("Arial", "", 12)
        pdf.cell(200, 10, txt=f"Net Cash Flow: {format_currency(net_cash)}", ln=2)
        pdf.cell(200, 10, txt=f"Total Income: {format_currency(income)}", ln=3)
        pdf.cell(200, 10, txt=f"Total Expenses: {format_currency(expenses)}", ln=4)
        pdf.ln(10)
        pdf.multi_cell(0, 10, f"Board Notes:\n{board_notes}")
        pdf.output("FundSight_Report.pdf")
        with open("FundSight_Report.pdf", "rb") as f:
            st.download_button("Download Report", f, file_name="FundSight_Report.pdf")

    # Email
    st.subheader("📧 Email Report")
    email_to = st.text_input("Recipient Email", value="jacob.b.franco@gmail.com")
    if st.button("Send Email"):
        if not os.path.exists("FundSight_Report.pdf"):
            st.error("Generate the PDF first.")
        else:
            msg = MIMEMultipart()
            msg["From"] = os.getenv("EMAIL_USER", "your_email@example.com")
            msg["To"] = email_to
            msg["Subject"] = f"FundSight Report - {selected_client}"
            msg.attach(MIMEText("See attached report.", "plain"))
            with open("FundSight_Report.pdf", "rb") as f:
                part = MIMEApplication(f.read(), _subtype="pdf")
                part.add_header("Content-Disposition", "attachment", filename="FundSight_Report.pdf")
                msg.attach(part)
            try:
                server = smtplib.SMTP("smtp.gmail.com", 587)
                server.starttls()
                server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
                server.send_message(msg)
                server.quit()
                st.success("✅ Email sent.")
            except Exception as e:
                st.error(f"❌ Email error: {e}")
else:
    st.info("👈 Upload a QuickBooks CSV to get started.")
