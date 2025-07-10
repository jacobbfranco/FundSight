# FundSight: Full Polished App with All Dashboard Features and Branding

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

# --- Page Config ---
st.set_page_config(page_title="FundSight Dashboard", layout="wide", page_icon="📊")

# --- Branding: Logo and Header ---
st.image("fundsight_logo.png", width=200)  # Ensure logo is available in same directory
st.markdown("<h1 style='text-align:center;'>📊 FundSight: Nonprofit Finance Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align:center; color:gray;'>Built for Habitat for Humanity Affiliates</h4>", unsafe_allow_html=True)
st.markdown("<hr style='margin-top:10px; margin-bottom:30px;'>", unsafe_allow_html=True)

# --- Sidebar: Client & File Uploads ---
client_names = ["Client A", "Client B", "Client C"]
selected_client = st.sidebar.selectbox("Select Client", client_names)

st.sidebar.markdown("### 📂 Upload Files")
uploaded_file = st.sidebar.file_uploader("Upload QuickBooks CSV", type=["csv"])
budget_file = st.sidebar.file_uploader("Upload Budget CSV", type=["csv"])
tag_file = st.sidebar.file_uploader("Upload Tag CSV (optional)", type=["csv"])
mortgage_file = st.sidebar.file_uploader("Upload Mortgage CSV (optional)", type=["csv"])

# --- Sidebar: Feature Toggles ---
st.sidebar.markdown("### ⚙️ Dashboard Options")
show_mortgages = st.sidebar.checkbox("Show Mortgage Tracking", value=True)
show_board = st.sidebar.checkbox("Show Board Report Options", value=True)

# --- Helper Functions ---
def format_currency(value):
    return f"${value:,.2f}" if value >= 0 else f"(${abs(value):,.2f})"

def styled_metric(icon, label, value):
    return f"""
    <div style='background-color:#f9f9f9; padding:20px; border-radius:15px; box-shadow:2px 2px 10px rgba(0,0,0,0.1); text-align:center'>
        <div style='font-size:32px'>{icon}</div>
        <div style='font-size:18px; font-weight:bold; margin-top:5px'>{label}</div>
        <div style='font-size:24px; color:#2e8b57; margin-top:5px'>{value}</div>
    </div>
    """

def add_section_divider():
    st.markdown("<hr style='margin-top:30px; margin-bottom:30px;'>", unsafe_allow_html=True)

# --- Load Main CSV File ---
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
    df = df.dropna(subset=["Date"])

    # Optional Tags
    tags = {}
    if tag_file:
        try:
            tag_df = pd.read_csv(tag_file)
            tags = dict(zip(tag_df["Transaction"], tag_df["Tag"]))
        except Exception:
            st.warning("⚠️ Could not read Tag CSV. Make sure it has 'Transaction' and 'Tag' columns.")

    # --- KPI Metrics ---
    total_income = df[df["Amount"] > 0]["Amount"].sum()
    total_expenses = df[df["Amount"] < 0]["Amount"].sum()
    net_cash = total_income + total_expenses

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(styled_metric("🟢", "Total Income", format_currency(total_income)), unsafe_allow_html=True)
    with col2:
        st.markdown(styled_metric("🔴", "Total Expenses", format_currency(total_expenses)), unsafe_allow_html=True)
    with col3:
        st.markdown(styled_metric("💰", "Net Cash Flow", format_currency(net_cash)), unsafe_allow_html=True)

    add_section_divider()

    # --- 30-Day Forecast ---
    st.markdown("📈 <b>30-Day Forecast</b>", unsafe_allow_html=True)
    forecast_df = df.copy()
    forecast_df = forecast_df.groupby(df["Date"].dt.date)["Amount"].sum().reset_index()
    forecast_df = forecast_df.rename(columns={"Date": "Day"})
    forecast_df["Day"] = pd.to_datetime(forecast_df["Day"], errors='coerce')
    forecast_df = forecast_df.set_index("Day").resample("D").sum().fillna(0).cumsum()

    fig, ax = plt.subplots()
    ax.plot(forecast_df.index, forecast_df["Amount"], linewidth=2)
    ax.set_title("Cumulative Cash Flow Forecast", fontsize=14)
    ax.set_ylabel("Amount ($)")
    ax.set_xlabel("Date")
    ax.grid(True)
    st.pyplot(fig)

    add_section_divider()

    # --- Expenses by Category ---
    st.markdown("📊 <b>Expenses by Category</b>", unsafe_allow_html=True)
    if "Category" in df.columns:
        expense_summary = df[df["Amount"] < 0].groupby("Category")["Amount"].sum().sort_values()
        st.bar_chart(expense_summary.abs())
    else:
        st.warning("⚠️ 'Category' column not found in the uploaded file.")

    add_section_divider()

    # --- Budget vs Actuals ---
    st.markdown("📊 <b>Budget vs Actuals</b>", unsafe_allow_html=True)
    if budget_file:
        try:
            budget_df = pd.read_csv(budget_file)
            if "Category" in budget_df.columns and "Budget" in budget_df.columns:
                actuals = df[df["Amount"] < 0].groupby("Category")["Amount"].sum().abs()
                comparison = budget_df.set_index("Category")[["Budget"]].join(actuals.rename("Actual")).fillna(0)
                comparison["Variance"] = comparison["Budget"] - comparison["Actual"]
                st.dataframe(comparison.style.format("${:,.2f}"))
            else:
                st.warning("⚠️ Budget CSV must include 'Category' and 'Budget' columns.")
        except Exception:
            st.warning("⚠️ Error reading the budget file.")
    else:
        st.info("Upload a Budget CSV file to see budget vs actuals.")

    add_section_divider()

    # --- Financial Ratios ---
    st.markdown("📊 <b>Financial Ratios</b>", unsafe_allow_html=True)
    income = df[df["Amount"] > 0]["Amount"].sum()
    expenses = abs(df[df["Amount"] < 0]["Amount"].sum())
    if expenses > 0:
        savings_ratio = (income - expenses) / expenses
        burn_rate = expenses / 30
        st.markdown(f"**Savings Ratio:** {savings_ratio:.2f}")
        st.markdown(f"**Burn Rate (Monthly):** ${burn_rate:,.2f}")
    else:
        st.info("Not enough data to calculate ratios.")

    add_section_divider()

    # --- Alerts Section ---
    st.markdown("🚨 <b>Alerts & Thresholds</b>", unsafe_allow_html=True)
    cash_threshold = st.sidebar.number_input("Low Cash Warning Threshold", value=5000)
    if net_cash < cash_threshold:
        st.error(f"⚠️ Cash is below threshold: {format_currency(net_cash)}")

    high_expense_limit = st.sidebar.number_input("High Expense Alert", value=10000)
    large_expenses = df[df["Amount"] < -high_expense_limit]
    if not large_expenses.empty:
        st.warning("⚠️ High expenses detected:")
        cols_to_show = [col for col in ["Date", "Description", "Amount"] if col in df.columns]
        st.dataframe(large_expenses[cols_to_show])

    add_section_divider()

    # --- Mortgage Tracking ---
    st.markdown("🏠 <b>Mortgage Tracking Module</b>", unsafe_allow_html=True)
    mortgage_file = st.sidebar.file_uploader("Upload Mortgage CSV (optional)", type=["csv"])
    if mortgage_file:
        mortgage_df = pd.read_csv(mortgage_file)
        if {"Homeowner", "Loan Amount", "Remaining Balance", "Delinquent"}.issubset(mortgage_df.columns):
            total_loans = mortgage_df["Loan Amount"].sum()
            total_balance = mortgage_df["Remaining Balance"].sum()
            delinquent_accounts = mortgage_df[mortgage_df["Delinquent"] > 0].shape[0]

            st.write(f"**Total Mortgages Issued:** {format_currency(total_loans)}")
            st.write(f"**Outstanding Balance:** {format_currency(total_balance)}")
            st.write(f"**Delinquent Accounts:** {delinquent_accounts}")

            st.dataframe(mortgage_df)
        else:
            st.warning("Mortgage file must include: Homeowner, Loan Amount, Remaining Balance, Delinquent")

    add_section_divider()

    # --- Scenario Modeling ---
    st.markdown("🔮 <b>Scenario Modeling</b>", unsafe_allow_html=True)
    adj_income = st.number_input("Adjusted Income Projection", value=float(total_income))
    adj_expenses = st.number_input("Adjusted Expense Projection", value=float(abs(total_expenses)))
    projected_net = adj_income - adj_expenses
    st.markdown(f"**Projected Net Cash:** {format_currency(projected_net)}")

    add_section_divider()

    # --- Board Notes Section ---
    st.markdown("📝 <b>Board Notes</b>", unsafe_allow_html=True)
    board_notes = st.text_area("Enter any notes to include in the board report:", key="board_notes")

    add_section_divider()

    # --- PDF Report Generator ---
    st.markdown("📤 <b>Download PDF Report</b>", unsafe_allow_html=True)
    if st.button("Generate PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(200, 10, txt=f"FundSight Report - {selected_client}", ln=1, align='C')
        pdf.set_font("Arial", "", 12)
        pdf.ln(10)
        pdf.cell(200, 10, txt=f"Net Cash Flow: {format_currency(net_cash)}", ln=1)
        pdf.cell(200, 10, txt=f"Total Income: {format_currency(total_income)}", ln=1)
        pdf.cell(200, 10, txt=f"Total Expenses: {format_currency(total_expenses)}", ln=1)
        pdf.ln(10)
        pdf.multi_cell(0, 10, f"Board Notes:\n{board_notes}")
        pdf.output("FundSight_Report.pdf")
        with open("FundSight_Report.pdf", "rb") as f:
            st.download_button("📥 Download Report", f, file_name="FundSight_Report.pdf")

    add_section_divider()

    # --- Email PDF ---
    st.markdown("📧 <b>Email Report</b>", unsafe_allow_html=True)
    email_to = st.text_input("Recipient Email", value="jacob.b.franco@gmail.com")
    email_btn = st.button("Send Report via Email")
    if email_btn:
        if not os.path.exists("FundSight_Report.pdf"):
            st.error("⚠️ Please generate the PDF first.")
        else:
            msg = MIMEMultipart()
            msg["From"] = os.getenv("EMAIL_USER", "your_email@example.com")
            msg["To"] = email_to
            msg["Subject"] = f"FundSight Report - {selected_client}"
            body = f"Attached is the FundSight report for {selected_client}.\n\nBoard Notes:\n{board_notes}"
            msg.attach(MIMEText(body, "plain"))

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
                st.success("✅ Email sent successfully.")
            except Exception as e:
                st.error(f"❌ Email failed to send: {e}")

else:
    st.info("👈 Upload a QuickBooks CSV to see your full dashboard.")

# --- Footer ---
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    "<div style='text-align:center; color:gray;'>"
    "FundSight © 2025 | Built for mission-driven teams."
    "</div>",
    unsafe_allow_html=True,
)
