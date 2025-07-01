import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
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
client_names = ["Client A", "Client B", "Client C"]
selected_client = st.sidebar.selectbox("Select Client", client_names)

# Uploads
st.sidebar.markdown(f"### Upload files for {selected_client}")
uploaded_file = st.sidebar.file_uploader("Upload QuickBooks CSV", type=["csv"], key=f"{selected_client}_qb")
budget_file = st.sidebar.file_uploader("Upload Budget CSV (optional)", type=["csv"], key=f"{selected_client}_budget")

if uploaded_file:
    st.markdown(f"### 📂 Dashboard for `{selected_client}`")
    df = pd.read_csv(uploaded_file)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Account"] = df["Account"].str.strip()
    if "Name" in df.columns:
        df["Name"] = df["Name"].fillna("Unknown")

    income = df[df["Amount"] > 0]["Amount"].sum()
    expenses = df[df["Amount"] < 0]["Amount"].sum()
    net = income + expenses

    col1, col2, col3 = st.columns(3)
    col1.metric("🟢 Total Income", f"${income:,.2f}")
    col2.metric("🔴 Total Expenses", f"${expenses:,.2f}")
    col3.metric("💰 Net Cash Flow", f"${net:,.2f}")
    st.markdown("---")

    # 📊 Charts and graphs
    charts = []

    # 1. Daily Cash Flow
    daily_totals = df.groupby("Date")["Amount"].sum().reset_index()
    fig1, ax1 = plt.subplots()
    ax1.plot(daily_totals["Date"], daily_totals["Amount"])
    ax1.set_title("Daily Cash Flow")
    fig1.tight_layout()
    fig1.savefig("/tmp/daily_cash_flow.png")
    charts.append("/tmp/daily_cash_flow.png")
    st.line_chart(daily_totals.set_index("Date"))

    # 2. Expenses by Account
    expense_df = df[df["Amount"] < 0]
    by_category = expense_df.groupby("Account")["Amount"].sum().sort_values()
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    ax2.barh(by_category.index, by_category.abs())
    ax2.set_title("Expenses by Account")
    fig2.tight_layout()
    fig2.savefig("/tmp/expenses_by_account.png")
    charts.append("/tmp/expenses_by_account.png")
    st.bar_chart(by_category.abs())

    # 3. Top Revenue Sources
    if "Name" in df.columns:
        top_sources = df[df["Amount"] > 0].groupby("Name")["Amount"].sum().sort_values(ascending=False).head(10)
        fig3, ax3 = plt.subplots(figsize=(10, 6))
        ax3.bar(top_sources.index, top_sources.values)
        ax3.set_title("Top Revenue Sources")
        plt.xticks(rotation=45, ha='right')
        fig3.tight_layout()
        fig3.savefig("/tmp/top_revenue_sources.png")
        charts.append("/tmp/top_revenue_sources.png")
        st.bar_chart(top_sources)

    # 4. Monthly Trend
    monthly_trend = df.groupby(df["Date"].dt.to_period("M"))["Amount"].sum().reset_index()
    monthly_trend["Date"] = monthly_trend["Date"].astype(str)
    fig4, ax4 = plt.subplots()
    ax4.plot(monthly_trend["Date"], monthly_trend["Amount"])
    ax4.set_title("Monthly Financial Trend")
    plt.xticks(rotation=45, ha='right')
    fig4.tight_layout()
    fig4.savefig("/tmp/monthly_trend.png")
    charts.append("/tmp/monthly_trend.png")
    st.line_chart(monthly_trend.set_index("Date"))

    # --- PDF Report Generation ---
    class PDF(FPDF):
        def header(self):
            self.set_font("Arial", "B", 14)
            self.cell(0, 10, "FundSight Financial Report", ln=True, align="C")

        def chapter_title(self, title):
            self.set_font("Arial", "B", 12)
            self.cell(0, 10, f"{title}", ln=True, align="L")

        def add_chart(self, image_path):
            self.image(image_path, w=180)
            self.ln(10)

    pdf = PDF()
    pdf.add_page()

    # 📄 Summary Section
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "📊 Financial Summary", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"🟢 Total Income: ${income:,.2f}", ln=True)
    pdf.cell(0, 10, f"🔴 Total Expenses: ${expenses:,.2f}", ln=True)
    pdf.cell(0, 10, f"💰 Net Cash Flow: ${net:,.2f}", ln=True)
    pdf.ln(5)

    for chart in charts:
        pdf.chapter_title(os.path.splitext(os.path.basename(chart))[0].replace("_", " ").title())
        pdf.add_chart(chart)

    pdf_path = f"/tmp/{selected_client}_fundsight_report.pdf"
    pdf.output(pdf_path)

    # 📧 EMAIL REPORT
    st.subheader("📧 Send Full Report via Email (PDF)")
    if st.button("Send Report to jacob.b.franco@gmail.com"):
        try:
            sender_email = st.secrets["email_user"]
            sender_password = st.secrets["email_password"]
            msg = MIMEMultipart()
            msg["From"] = sender_email
            msg["To"] = "jacob.b.franco@gmail.com"
            msg["Subject"] = f"FundSight PDF Report - {selected_client}"
            body = f"""Attached is the full PDF FundSight report for {selected_client}.

🟢 Total Income: ${income:,.2f}
🔴 Total Expenses: ${expenses:,.2f}
💰 Net Cash Flow: ${net:,.2f}
"""
            msg.attach(MIMEText(body, "plain"))

            with open(pdf_path, "rb") as f:
                part = MIMEApplication(f.read(), _subtype="pdf")
                part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf_path))
                msg.attach(part)

            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(msg["From"], msg["To"], msg.as_string())
            server.quit()
            st.success("✅ PDF Report sent successfully.")
        except Exception as e:
            st.error(f"❌ Failed to send PDF: {e}")

else:
    st.info("📤 Please upload a QuickBooks CSV file to get started.")
