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

# --------------------
# SETUP & TITLE
# --------------------
st.set_page_config(page_title="FundSight Dashboard", layout="wide", page_icon="📊")
st.image("fundsight_logo.png", width=200)
st.markdown("### Welcome to FundSight – your all-in-one dashboard for nonprofit financial health.")

# --------------------
# CLIENT & FILE UPLOADS
# --------------------
st.sidebar.header("👥 Client Selection")
client_names = ["Client A", "Client B", "Client C"]
selected_client = st.sidebar.selectbox("Select Client", client_names)

st.sidebar.markdown(f"### Upload files for {selected_client}")
uploaded_file = st.sidebar.file_uploader("Upload QuickBooks CSV", type=["csv"], key=f"{selected_client}_qb")
budget_file = st.sidebar.file_uploader("Upload Budget CSV (optional)", type=["csv"], key=f"{selected_client}_budget")
mortgage_file = st.sidebar.file_uploader("Upload Mortgage CSV", type=["csv"], key="mortgage_csv")

# Show Email Button
show_board_email = st.sidebar.checkbox("📤 Enable Board Report Email")

# --------------------
# MAIN DASHBOARD
# --------------------
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

    # Scenario Modeling
    st.subheader("🔄 Scenario Modeling")
    donation_increase = st.slider("Donation Increase (%)", -50, 100, 0)
    expense_reduction = st.slider("Expense Reduction (%)", 0, 50, 0)
    scenario_income = income * (1 + donation_increase / 100)
    scenario_expense = expenses * (1 - expense_reduction / 100)
    scenario_net = scenario_income + scenario_expense
    st.write(f"📈 Projected Net Cash Flow: ${scenario_net:,.2f}")

    # Multi-Year Comparison
    st.subheader("📆 Multi-Year Comparison")
    if df["Date"].dt.year.nunique() > 1:
        st.bar_chart(df.groupby(df["Date"].dt.year)["Amount"].sum())

    # Financial Ratios
    st.subheader("📊 Key Financial Ratios")
    monthly_avg_expense = abs(df[df["Amount"] < 0].set_index("Date")["Amount"].resample("M").sum().mean())
    days_cash = (cash_on_hand / monthly_avg_expense * 30) if monthly_avg_expense else 0
    program_ratio = abs(df[df["Amount"] < 0]["Amount"].sum()) / abs(df["Amount"].sum())
    st.metric("💵 Days Cash on Hand", f"{days_cash:,.1f}")
    st.metric("📊 Program Expense Ratio", f"{program_ratio:.2%}")

    # Alerts
    st.subheader("🔔 Alerts")
    cash_threshold = st.number_input("Minimum Cash Threshold", value=5000)
    if cash_on_hand < cash_threshold:
        st.error("⚠️ Alert: Cash on hand is below threshold.")
    else:
        st.success("✅ Cash on hand is sufficient.")

    # Budget vs Actuals
    if budget_file:
        st.subheader("📊 Budget vs Actuals")
        budget_df = pd.read_csv(budget_file)
        if "Actual" not in budget_df.columns and "Budget Amount" in budget_df.columns:
            actuals = df.groupby("Account")["Amount"].sum().reset_index()
            actuals.rename(columns={"Amount": "Actual"}, inplace=True)
            budget_df = pd.merge(budget_df, actuals, on="Account", how="left")
        if "Budget Amount" in budget_df.columns and "Actual" in budget_df.columns:
            budget_df["Variance"] = budget_df["Budget Amount"] - budget_df["Actual"]
        st.dataframe(budget_df)

# --------------------
# MORTGAGE TRACKER
# --------------------
if mortgage_file:
    st.subheader("🏠 Mortgage Tracker")
    mortgage_df = pd.read_csv(mortgage_file)
    if all(col in mortgage_df.columns for col in ["Borrower", "Loan ID", "Amount Due", "Amount Paid", "Due Date"]):
        mortgage_df["Balance"] = mortgage_df["Amount Due"] - mortgage_df["Amount Paid"]
        mortgage_df["Due Date"] = pd.to_datetime(mortgage_df["Due Date"])
        mortgage_df["Days Late"] = (pd.Timestamp.today() - mortgage_df["Due Date"]).dt.days
        mortgage_df["Delinquent"] = mortgage_df["Days Late"] > 60

        st.metric("Total Outstanding Balance", f"${mortgage_df['Balance'].sum():,.2f}")
        st.metric("🚨 Delinquent Loans", mortgage_df['Delinquent'].sum())

        delinquency_counts = mortgage_df['Delinquent'].value_counts()
        values = [delinquency_counts.get(False, 0), delinquency_counts.get(True, 0)]
        labels = ["Current", "Delinquent"]

        fig, ax = plt.subplots()
        ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
        ax.axis("equal")
        st.pyplot(fig)

        st.bar_chart(mortgage_df.set_index("Loan ID")["Balance"])
        st.dataframe(mortgage_df)

# --------------------
# EMAIL REPORT SECTION
# --------------------
if uploaded_file and show_board_email:
    st.markdown("### 📤 Send PDF Report")
    if st.button("Send PDF Report"):
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt=f"Board Summary Report - {selected_client}", ln=True)
            pdf.cell(200, 10, txt=f"Total Income: ${income:,.2f}", ln=True)
            pdf.cell(200, 10, txt=f"Total Expenses: ${expenses:,.2f}", ln=True)
            pdf.cell(200, 10, txt=f"Net Cash Flow: ${net:,.2f}", ln=True)
            pdf.cell(200, 10, txt=f"Days Cash on Hand: {days_cash:.1f}", ln=True)
            pdf.cell(200, 10, txt=f"Program Expense Ratio: {program_ratio:.2%}", ln=True)
            pdf.cell(200, 10, txt=f"Scenario Net Cash Flow: ${scenario_net:,.2f}", ln=True)

            pdf_output = "/tmp/fundsight_report.pdf"
            pdf.output(pdf_output.encode("latin-1"))

            msg = MIMEMultipart()
            msg["From"] = "jacob.b.franco@gmail.com"
            msg["To"] = "jacob.b.franco@gmail.com"
            msg["Subject"] = f"Board Report for {selected_client}"
            body = MIMEText("Attached is the latest board summary from FundSight.", "plain")
            msg.attach(body)

            with open(pdf_output, "rb") as f:
                attachment = MIMEApplication(f.read(), _subtype="pdf")
                attachment.add_header("Content-Disposition", "attachment", filename="fundsight_report.pdf")
                msg.attach(attachment)

            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login("jacob.b.franco@gmail.com", "cote lzmi cwpt knkw")
                server.send_message(msg)

            st.success("✅ PDF with logo, charts, and summary was generated and emailed!")

        except Exception as e:
            st.error(f"Error sending email: {e}")

# --------------------
# FOOTER
# --------------------
footer = """
<style>
.footer {
    position: fixed;
    bottom: 0;
    width: 100%;
    background: #f1f1f1;
    color: #555;
    text-align: center;
    padding: 10px;
}
</style>
<div class="footer">
    FundSight © 2025 | Built for Nonprofits
</div>
"""
st.markdown(footer, unsafe_allow_html=True)
