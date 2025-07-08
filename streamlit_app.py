# Full FundSight App
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

# --- Helper: Format currency with parentheses for negatives ---
def format_currency(value):
    if value < 0:
        return f"(${abs(value):,.2f})"
    else:
        return f"${value:,.2f}"

# --- App Setup ---
st.set_page_config(page_title="FundSight Dashboard", layout="wide", page_icon="📊")
st.image("fundsight_logo.png", width=200)

# --- Sidebar ---
st.sidebar.header("👥 Client Selection")
clients = ["Client A", "Client B", "Client C"]
selected_client = st.sidebar.selectbox("Select Client", clients)

uploaded_file = st.sidebar.file_uploader("Upload QuickBooks CSV", type="csv")
budget_file = st.sidebar.file_uploader("Upload Budget CSV (optional)", type="csv")
mortgage_file = st.sidebar.file_uploader("Upload Mortgage CSV (optional)", type="csv")

include_signature = st.sidebar.checkbox("🖋 Include Signature Section")
show_email_button = st.sidebar.checkbox("📤 Enable Email to Board")

# --- Main Header ---
st.markdown(f"""
## FundSight Dashboard for {selected_client}  
<span style='font-size:16px; color:gray;'>Built for Nonprofits • Financial Clarity at a Glance</span>
""", unsafe_allow_html=True)

# --- Load & Process Main Data ---
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
    col1.metric("🟢 Total Income", format_currency(income))
    col2.metric("🔴 Total Expenses", format_currency(expenses))
    col3.metric("💰 Net Cash Flow", format_currency(net))
    st.markdown("---")

    # --- Scenario Modeling ---
    st.subheader("🔄 Scenario Modeling")
    donation_increase = st.slider("📈 Donation Increase (%)", -50, 100, 0)
    grant_change = st.slider("🏛️ Grant Revenue Change (%)", -50, 100, 0)
    personnel_change = st.slider("👥 Personnel Expense Change (%)", -50, 50, 0)
    program_change = st.slider("🧱 Program Expense Change (%)", -50, 50, 0)
    unexpected_cost = st.number_input("⚠️ One-Time Unexpected Cost ($)", min_value=0, value=0, step=1000)

    personnel_expense = df[df["Account"].str.contains("Salary|Wages|Payroll", case=False, na=False)]["Amount"].sum()
    program_expense = df[df["Account"].str.contains("Program|Construction|Materials|Supplies", case=False, na=False)]["Amount"].sum()
    other_expense = expenses - (personnel_expense + program_expense)

    scenario_income = (income * (1 + donation_increase / 100)) + (income * (grant_change / 100))
    scenario_expenses = (personnel_expense * (1 + personnel_change / 100)) + (program_expense * (1 + program_change / 100)) + other_expense + (-unexpected_cost)
    scenario_net = scenario_income + scenario_expenses

    st.markdown("### 📉 Projected Scenario Outcome")
    st.metric("📈 Adjusted Net Cash Flow", format_currency(scenario_net))
    st.caption("This projection includes selected revenue and expense changes.")

    # --- Multi-Year Comparison ---
    st.subheader("📆 Multi-Year Comparison")
    if df["Date"].dt.year.nunique() > 1:
        st.bar_chart(df.groupby(df["Date"].dt.year)["Amount"].sum())

    # --- Financial KPIs ---
    st.subheader("📊 Key Financial Ratios")
    monthly_avg_expense = abs(df[df["Amount"] < 0].set_index("Date")["Amount"].resample("M").sum().mean())
    days_cash = (cash_on_hand / monthly_avg_expense * 30) if monthly_avg_expense else 0
    program_ratio = abs(df[df["Amount"] < 0]["Amount"].sum()) / abs(df["Amount"].sum())
    st.metric("💵 Days Cash on Hand", f"{days_cash:,.1f}")
    st.metric("📊 Program Expense Ratio", f"{program_ratio:.2%}")

    # --- Alerts ---
    st.subheader("🔔 Alerts")
    cash_threshold = st.number_input("Minimum Cash Threshold", value=5000)
    if cash_on_hand < cash_threshold:
        st.error("⚠️ Alert: Cash on hand is below threshold.")
    else:
        st.success("✅ Cash on hand is sufficient.")

    # --- Budget vs Actuals ---
    if budget_file is not None:
        st.subheader("📊 Budget vs Actuals")
        budget_df = pd.read_csv(budget_file)
        if "Actual" not in budget_df.columns and "Budget Amount" in budget_df.columns:
            actuals = df.groupby("Account")["Amount"].sum().reset_index()
            actuals.rename(columns={"Amount": "Actual"}, inplace=True)
            budget_df = pd.merge(budget_df, actuals, on="Account", how="left")
        budget_df["Variance"] = budget_df["Budget Amount"] - budget_df["Actual"]
        st.dataframe(budget_df)

# --- Mortgage Tracker ---
mortgage_summary = ""
if mortgage_file:
    st.subheader("🏠 Mortgage Tracker")
    mortgage_df = pd.read_csv(mortgage_file)
    if all(col in mortgage_df.columns for col in ["Borrower", "Loan ID", "Amount Due", "Amount Paid", "Due Date"]):
        mortgage_df["Balance"] = mortgage_df["Amount Due"] - mortgage_df["Amount Paid"]
        mortgage_df["Due Date"] = pd.to_datetime(mortgage_df["Due Date"])
        mortgage_df["Days Late"] = (pd.Timestamp.today() - mortgage_df["Due Date"]).dt.days
        mortgage_df["Delinquent"] = mortgage_df["Days Late"] > 60

        st.metric("Total Outstanding Balance", format_currency(mortgage_df["Balance"].sum()))
        st.metric("🚨 Delinquent Loans", mortgage_df["Delinquent"].sum())

        delinquency_counts = mortgage_df['Delinquent'].value_counts()
        values = [delinquency_counts.get(False, 0), delinquency_counts.get(True, 0)]
        labels = ["Current", "Delinquent"]

        fig, ax = plt.subplots()
        ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
        ax.axis("equal")
        st.pyplot(fig)

        st.bar_chart(mortgage_df.set_index("Loan ID")["Balance"])
        st.dataframe(mortgage_df)

        mortgage_summary = f"Delinquent Loans: {mortgage_df['Delinquent'].sum()}\nOutstanding Balance: {format_currency(mortgage_df['Balance'].sum())}"

# --- Board Notes ---
st.markdown("### 📝 Board Notes")
board_notes = st.text_area("Enter any notes you'd like to include in the Board PDF report:", height=150)

# --- Email PDF ---
if show_email_button and uploaded_file:
    st.markdown("### 📤 Send PDF Report")
    if st.button("Send PDF Report"):
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            if os.path.exists("fundsight_logo.png"):
                pdf.image("fundsight_logo.png", x=10, y=10, w=30)
            pdf.set_font("Arial", "B", 12)
            pdf.set_xy(160, 10)
            pdf.cell(40, 10, f"{pd.Timestamp.today():%B %d, %Y}", align="R")
            pdf.ln(20)
            pdf.set_xy(10, 30)
            pdf.set_font("Arial", "", 12)
            pdf.cell(0, 10, f"Client: {selected_client}", ln=True)

            # Financial Summary
            pdf.ln(5)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "Board Financial Summary", ln=True)
            pdf.set_font("Arial", "", 12)
            pdf.cell(0, 10, f"Total Income:           {format_currency(income)}", ln=True)
            pdf.cell(0, 10, f"Total Expenses:         {format_currency(expenses)}", ln=True)
            pdf.cell(0, 10, f"Net Cash Flow:          {format_currency(net)}", ln=True)

            # Scenario Modeling
            pdf.ln(5)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "Scenario Modeling", ln=True)
            pdf.set_font("Arial", "", 12)
            pdf.cell(0, 10, f"Projected Net Cash Flow: {format_currency(scenario_net)}", ln=True)
            pdf.cell(0, 10, f"(Donation increase: {donation_increase:+}%, Grant change: {grant_change:+}%)", ln=True)

            # KPIs
            pdf.ln(5)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "Financial Ratios", ln=True)
            pdf.set_font("Arial", "", 12)
            pdf.cell(0, 10, f"Days Cash on Hand: {days_cash:,.1f}", ln=True)
            pdf.cell(0, 10, f"Program Expense Ratio: {program_ratio:.2%}", ln=True)

            # Mortgage
            if mortgage_summary:
                pdf.ln(5)
                pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 10, "Mortgage Summary", ln=True)
                pdf.set_font("Arial", "", 12)
                for line in mortgage_summary.split("\n"):
                    pdf.cell(0, 10, line, ln=True)

            # Notes
            if board_notes.strip():
                pdf.ln(5)
                pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 10, "Board Notes", ln=True)
                pdf.set_font("Arial", "", 12)
                pdf.multi_cell(0, 10, board_notes)

            if include_signature:
                pdf.ln(10)
                pdf.cell(0, 10, "_____________________", ln=True)
                pdf.cell(0, 10, "Board Member Signature", ln=True)

            pdf.set_y(-20)
            pdf.set_font("Arial", "I", 10)
            pdf.cell(0, 10, "FundSight © 2025 | Built for Nonprofits", 0, 0, "C")

            # Save and email
            output_path = "/tmp/fundsight_board_report.pdf"
            pdf.output(output_path)

            msg = MIMEMultipart()
            msg["From"] = st.secrets["email"]["email_user"]
            msg["To"] = st.secrets["email"]["email_user"]
            msg["Subject"] = f"Board Report for {selected_client}"
            msg.attach(MIMEText("Attached is your FundSight Board Summary Report.", "plain"))

            with open(output_path, "rb") as f:
                part = MIMEApplication(f.read(), _subtype="pdf")
                part.add_header("Content-Disposition", "attachment", filename="fundsight_board_report.pdf")
                msg.attach(part)

            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(st.secrets["email"]["email_user"], st.secrets["email"]["email_password"])
                server.send_message(msg)

            st.success("✅ PDF sent successfully.")

        except Exception as e:
            st.error(f"Error sending PDF: {e}")
