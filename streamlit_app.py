import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import timedelta
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from fpdf import FPDF
import os

st.set_page_config(page_title="FundSight: Nonprofit Finance Dashboard", layout="wide")
st.title("📊 FundSight: QuickBooks Dashboard for Nonprofits")

# --- CLIENT SELECTION ---
st.sidebar.header("👥 Client Selection")
client_names = ["Client A", "Client B", "Client C"]
selected_client = st.sidebar.selectbox("Select Client", client_names)

# --- UPLOADS ---
st.sidebar.markdown(f"### Upload files for {selected_client}")
uploaded_file = st.sidebar.file_uploader("Upload QuickBooks CSV", type=["csv"], key=f"{selected_client}_qb")
budget_file = st.sidebar.file_uploader("Upload Budget CSV (optional)", type=["csv"], key=f"{selected_client}_budget")

# --- MAIN DASHBOARD ---
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Account"] = df["Account"].str.strip()
    if "Name" in df.columns:
        df["Name"] = df["Name"].fillna("Unknown")

    st.header(f"📂 Dashboard for `{selected_client}`")

    income = df[df["Amount"] > 0]["Amount"].sum()
    expenses = df[df["Amount"] < 0]["Amount"].sum()
    net = income + expenses

    col1, col2, col3 = st.columns(3)
    col1.metric("🟢 Total Income", f"${income:,.2f}")
    col2.metric("🔴 Total Expenses", f"${expenses:,.2f}")
    col3.metric("💰 Net Cash Flow", f"${net:,.2f}")

    st.markdown("---")

    # Daily Cash Flow
    st.subheader("📈 Daily Cash Flow Trend")
    daily_totals = df.groupby("Date")["Amount"].sum().reset_index()
    st.line_chart(daily_totals.set_index("Date"))

    # Expenses by Category
    st.subheader("📊 Expenses by Account Category")
    expense_df = df[df["Amount"] < 0]
    by_category = expense_df.groupby("Account")["Amount"].sum().sort_values()
    st.bar_chart(by_category.abs())

    # Pie Chart
    st.subheader("🧁 Expense Distribution")
    fig1, ax1 = plt.subplots()
    ax1.pie(by_category.abs(), labels=by_category.index, autopct="%1.1f%%", startangle=90)
    ax1.axis("equal")
    st.pyplot(fig1)

    # Forecast
    st.subheader("📅 30-Day Cash Flow Projection")
    daily_avg = daily_totals["Amount"].mean()
    future_dates = pd.date_range(start=daily_totals["Date"].max() + timedelta(days=1), periods=30)
    forecast_df = pd.DataFrame({"Date": future_dates, "Amount": daily_avg})
    st.line_chart(forecast_df.set_index("Date"))

    # --- PDF Report Generation with Charts ---
    st.subheader("📧 Send PDF Report via Email")

    if st.button("📨 Send PDF Report"):
        try:
            # 1. Save charts
            chart_paths = []

            # Expenses by Category
            fig2, ax2 = plt.subplots(figsize=(6, 4))
            by_category.plot(kind="bar", ax=ax2)
            ax2.set_title("Expenses by Account")
            ax2.set_ylabel("Amount")
            fig2.tight_layout()
            chart1_path = "/tmp/expenses_by_account.png"
            fig2.savefig(chart1_path)
            chart_paths.append(chart1_path)

            # Daily Cash Flow
            fig3, ax3 = plt.subplots(figsize=(6, 4))
            ax3.plot(daily_totals["Date"], daily_totals["Amount"], marker="o")
            ax3.set_title("Daily Cash Flow")
            ax3.set_xlabel("Date")
            ax3.set_ylabel("Amount")
            fig3.autofmt_xdate()
            fig3.tight_layout()
            chart2_path = "/tmp/daily_cash_flow.png"
            fig3.savefig(chart2_path)
            chart_paths.append(chart2_path)

            # Forecast
            fig4, ax4 = plt.subplots(figsize=(6, 4))
            ax4.plot(forecast_df["Date"], forecast_df["Amount"], color="green")
            ax4.set_title("30-Day Cash Flow Forecast")
            ax4.set_xlabel("Date")
            ax4.set_ylabel("Amount")
            fig4.autofmt_xdate()
            fig4.tight_layout()
            chart3_path = "/tmp/forecast_chart.png"
            fig4.savefig(chart3_path)
            chart_paths.append(chart3_path)

            # 2. Generate PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, f"FundSight Financial Report - {selected_client}", ln=True)

            pdf.set_font("Arial", "", 12)
            pdf.ln(10)
            pdf.cell(0, 10, f"Total Income: ${income:,.2f}", ln=True)
            pdf.cell(0, 10, f"Total Expenses: ${expenses:,.2f}", ln=True)
            pdf.cell(0, 10, f"Net Cash Flow: ${net:,.2f}", ln=True)

            for chart_path in chart_paths:
                pdf.ln(10)
                pdf.image(chart_path, w=170)

            pdf_output_path = "/tmp/fundsight_report.pdf"
            pdf.output(pdf_output_path)

            # 3. Email the PDF
            sender_email = st.secrets["email_user"]
            sender_password = st.secrets["email_password"]
            recipient_email = "jacob.b.franco@gmail.com"

            msg = MIMEMultipart()
            msg["From"] = sender_email
            msg["To"] = recipient_email
            msg["Subject"] = f"FundSight PDF Report - {selected_client}"
            body = "Attached is the full FundSight PDF report with charts."

            msg.attach(MIMEText(body, "plain"))
            with open(pdf_output_path, "rb") as f:
                part = MIMEApplication(f.read(), _subtype="pdf")
                part.add_header("Content-Disposition", "attachment", filename="fundsight_report.pdf")
                msg.attach(part)

            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
            server.quit()

            st.success("✅ PDF report emailed successfully.")

        except Exception as e:
            st.error(f"❌ Failed to send email: {e}")

else:
    st.info("📤 Please upload a QuickBooks CSV file to get started.")
