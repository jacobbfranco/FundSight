import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fpdf import FPDF
import os

st.set_page_config(page_title="FundSight: Nonprofit Finance Dashboard", layout="wide")
st.title("FundSight: QuickBooks Dashboard for Nonprofits")

# --- MULTI-CLIENT SELECTION ---
st.sidebar.header("Client Selection")
client_names = ["Client A", "Client B", "Client C"]
selected_client = st.sidebar.selectbox("Select Client", client_names)

# Uploads
st.sidebar.markdown(f"### Upload files for {selected_client}")
uploaded_file = st.sidebar.file_uploader("Upload QuickBooks CSV", type=["csv"], key=f"{selected_client}_qb")
budget_file = st.sidebar.file_uploader("Upload Budget CSV (optional)", type=["csv"], key=f"{selected_client}_budget")

if uploaded_file:
    st.markdown(f"### Dashboard for {selected_client}")
    df = pd.read_csv(uploaded_file)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Account"] = df["Account"].str.strip()
    if "Name" in df.columns:
        df["Name"] = df["Name"].fillna("Unknown")

    income = df[df["Amount"] > 0]["Amount"].sum()
    expenses = df[df["Amount"] < 0]["Amount"].sum()
    net = income + expenses

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Income", f"${income:,.2f}")
    col2.metric("Total Expenses", f"${expenses:,.2f}")
    col3.metric("Net Cash Flow", f"${net:,.2f}")
    st.markdown("---")

    # --- Charts and Visuals to Save ---
    fig_paths = []

    # 1. Expense by Category Bar Chart
    expense_df = df[df["Amount"] < 0]
    by_category = expense_df.groupby("Account")["Amount"].sum().sort_values()
    fig1, ax1 = plt.subplots()
    by_category.abs().plot(kind="barh", ax=ax1)
    ax1.set_title("Expenses by Category")
    fig1.tight_layout()
    path1 = "/tmp/bar_category.png"
    fig1.savefig(path1)
    fig_paths.append(path1)
    st.subheader("Expenses by Account Category")
    st.pyplot(fig1)

    # 2. Pie Chart
    fig2, ax2 = plt.subplots()
    ax2.pie(by_category.abs(), labels=by_category.index, autopct="%1.1f%%", startangle=90)
    ax2.axis("equal")
    ax2.set_title("Expense Distribution")
    path2 = "/tmp/pie_chart.png"
    fig2.savefig(path2)
    fig_paths.append(path2)
    st.subheader("Expense Distribution")
    st.pyplot(fig2)

    # 3. Monthly Expense Drill-down (Stacked Bar)
    st.subheader("Monthly Expense Drill-down")
    monthly_expense = expense_df.groupby([df["Date"].dt.to_period("M"), "Account"])["Amount"].sum().unstack().fillna(0)
    fig3, ax3 = plt.subplots(figsize=(10, 5))
    monthly_expense.abs().plot(kind="bar", stacked=True, ax=ax3)
    ax3.set_title("Monthly Expense Drill-down (Stacked)")
    ax3.set_ylabel("Amount ($)")
    fig3.tight_layout()
    path3 = "/tmp/monthly_expense.png"
    fig3.savefig(path3)
    fig_paths.append(path3)
    st.pyplot(fig3)

    # --- KPI Metrics ---
    cash_on_hand = df["Amount"].sum()
    monthly_expense_avg = abs(df[df["Amount"] < 0].set_index("Date")["Amount"].resample("M").sum().mean())
    days_cash = (cash_on_hand / monthly_expense_avg * 30) if monthly_expense_avg else 0
    expense_ratio = abs(expense_df["Amount"].sum()) / abs(df["Amount"].sum()) if not df.empty else 0

    st.subheader("Key Financial Ratios")
    st.metric("Days Cash on Hand", f"{days_cash:,.1f}")
    st.metric("Program Expense Ratio", f"{expense_ratio:.2%}")

    # --- PDF + Email ---
    st.subheader("Generate and Send PDF Report")
    if st.button("Send PDF Report"):
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(200, 10, f"FundSight Report – {selected_client}", ln=True)

            pdf.set_font("Arial", "", 12)
            pdf.ln(10)
            pdf.cell(200, 10, f"Total Income: ${income:,.2f}", ln=True)
            pdf.cell(200, 10, f"Total Expenses: ${expenses:,.2f}", ln=True)
            pdf.cell(200, 10, f"Net Cash Flow: ${net:,.2f}", ln=True)
            pdf.ln(5)
            pdf.cell(200, 10, f"Days Cash on Hand: {days_cash:,.1f}", ln=True)
            pdf.cell(200, 10, f"Program Expense Ratio: {expense_ratio:.2%}", ln=True)

            # Insert Charts
            for chart in fig_paths:
                pdf.ln(10)
                pdf.image(chart, w=180)

            # Save PDF
            pdf_path = "/tmp/fundsight_full_report.pdf"
            pdf.output(pdf_path)

            # Compose Email
            sender_email = st.secrets["email_user"]
            sender_password = st.secrets["email_password"]
            msg = MIMEMultipart()
            msg["From"] = sender_email
            msg["To"] = "jacob.b.franco@gmail.com"
            msg["Subject"] = f"FundSight Dashboard Report - {selected_client}"

            body = f"""Hello,

Attached is the FundSight dashboard report for {selected_client}.

Summary:
- Income: ${income:,.2f}
- Expenses: ${expenses:,.2f}
- Net Cash Flow: ${net:,.2f}
- Days Cash on Hand: {days_cash:,.1f}
- Program Expense Ratio: {expense_ratio:.2%}

Regards,
FundSight
"""
            msg.attach(MIMEText(body, "plain"))

            # Attach PDF
            with open(pdf_path, "rb") as f:
                attach = MIMEText(f.read(), "base64", "utf-8")
                attach.add_header("Content-Disposition", "attachment", filename="fundsight_report.pdf")
                msg.attach(attach)

            # Send Email
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(msg["From"], msg["To"], msg.as_string())
            server.quit()

            st.success("✅ Report sent successfully!")

        except Exception as e:
            st.error(f"❌ Failed to send report: {e}")

else:
    st.info("📤 Please upload a QuickBooks CSV file to get started.")
