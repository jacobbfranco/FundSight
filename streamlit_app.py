import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import timedelta
from fpdf import FPDF
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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

    # Charts folder
    chart_dir = "/tmp/charts"
    os.makedirs(chart_dir, exist_ok=True)
    chart_files = []

    # --- Daily Cash Flow Trend ---
    st.subheader("📈 Daily Cash Flow Trend")
    daily_totals = df.groupby("Date")["Amount"].sum().reset_index()
    st.line_chart(daily_totals.set_index("Date"))
    fig1, ax1 = plt.subplots()
    ax1.plot(daily_totals["Date"], daily_totals["Amount"])
    ax1.set_title("Daily Cash Flow Trend")
    fig1.autofmt_xdate()
    daily_path = os.path.join(chart_dir, "daily_cash_flow.png")
    fig1.savefig(daily_path)
    chart_files.append(daily_path)

    # --- Expenses by Account Category ---
    st.subheader("📊 Expenses by Account Category")
    expense_df = df[df["Amount"] < 0]
    by_category = expense_df.groupby("Account")["Amount"].sum().sort_values()
    st.bar_chart(by_category.abs())
    fig2, ax2 = plt.subplots()
    by_category.abs().plot(kind="bar", ax=ax2)
    ax2.set_title("Expenses by Category")
    fig2.tight_layout()
    cat_path = os.path.join(chart_dir, "expenses_by_category.png")
    fig2.savefig(cat_path)
    chart_files.append(cat_path)

    # --- Expense Distribution Pie Chart ---
    st.subheader("🧁 Expense Distribution")
    fig3, ax3 = plt.subplots()
    ax3.pie(by_category.abs(), labels=by_category.index, autopct="%1.1f%%", startangle=90)
    ax3.axis("equal")
    st.pyplot(fig3)
    pie_path = os.path.join(chart_dir, "expense_distribution.png")
    fig3.savefig(pie_path)
    chart_files.append(pie_path)

    # --- 30-Day Forecast ---
    st.subheader("📅 30-Day Cash Flow Projection")
    daily_avg = daily_totals["Amount"].mean()
    future_dates = pd.date_range(start=daily_totals["Date"].max() + timedelta(days=1), periods=30)
    forecast_df = pd.DataFrame({"Date": future_dates, "Amount": daily_avg})
    st.line_chart(forecast_df.set_index("Date"))
    fig4, ax4 = plt.subplots()
    ax4.plot(forecast_df["Date"], forecast_df["Amount"])
    ax4.set_title("30-Day Forecast")
    fig4.autofmt_xdate()
    forecast_path = os.path.join(chart_dir, "30_day_forecast.png")
    fig4.savefig(forecast_path)
    chart_files.append(forecast_path)

    # --- Budget vs Actuals ---
    if budget_file is not None:
        st.subheader("📋 Budget vs Actuals")
        budget_df = pd.read_csv(budget_file)
        budget_df.columns = budget_df.columns.str.strip()
        budget_df["Account"] = budget_df["Account"].str.strip()
        if {"Account", "Budget Amount"}.issubset(budget_df.columns):
            actuals = df.groupby("Account")["Amount"].sum()
            comparison = pd.merge(budget_df, actuals.rename("Actual"), on="Account", how="outer").fillna(0)
            comparison["Variance"] = comparison["Actual"] - comparison["Budget Amount"]
            st.dataframe(comparison)
            st.bar_chart(comparison.set_index("Account")[["Budget Amount", "Actual"]].abs())
            fig5, ax5 = plt.subplots()
            comparison[["Budget Amount", "Actual"]].abs().plot(kind="bar", ax=ax5)
            ax5.set_title("Budget vs Actuals")
            fig5.tight_layout()
            budget_path = os.path.join(chart_dir, "budget_vs_actuals.png")
            fig5.savefig(budget_path)
            chart_files.append(budget_path)

    # --- Trend Analysis ---
    st.subheader("📉 Trend Analysis")
    monthly_trend = df.groupby(df["Date"].dt.to_period("M"))["Amount"].sum().reset_index()
    monthly_trend["Date"] = monthly_trend["Date"].astype(str)
    st.line_chart(monthly_trend.set_index("Date"))
    fig6, ax6 = plt.subplots()
    ax6.plot(monthly_trend["Date"], monthly_trend["Amount"])
    ax6.set_title("Trend Analysis")
    fig6.autofmt_xdate()
    trend_path = os.path.join(chart_dir, "trend_analysis.png")
    fig6.savefig(trend_path)
    chart_files.append(trend_path)

    # --- Top Revenue Sources ---
    if "Name" in df.columns:
        st.subheader("💌 Top Revenue Sources")
        top_sources = df[df["Amount"] > 0].groupby("Name")["Amount"].sum().sort_values(ascending=False).head(10)
        st.bar_chart(top_sources)
        fig7, ax7 = plt.subplots()
        top_sources.plot(kind="bar", ax=ax7)
        ax7.set_title("Top Revenue Sources")
        fig7.tight_layout()
        top_rev_path = os.path.join(chart_dir, "top_revenue_sources.png")
        fig7.savefig(top_rev_path)
        chart_files.append(top_rev_path)

    # --- Monthly Expense Drill-down ---
    st.subheader("🔍 Monthly Expense Drill-down")
    expense_by_month = expense_df.groupby([df["Date"].dt.to_period("M"), "Account"])["Amount"].sum().unstack().fillna(0)
    st.line_chart(expense_by_month.abs())
    fig8, ax8 = plt.subplots()
    expense_by_month.abs().plot(ax=ax8)
    ax8.set_title("Monthly Expense Drill-down")
    fig8.tight_layout()
    drilldown_path = os.path.join(chart_dir, "monthly_expense_drilldown.png")
    fig8.savefig(drilldown_path)
    chart_files.append(drilldown_path)

    # --- Financial Ratios ---
    st.subheader("📊 Key Financial Ratios")
    cash_on_hand = df["Amount"].sum()
    monthly_expense_avg = abs(df[df["Amount"] < 0].set_index("Date")["Amount"].resample("M").sum().mean())
    days_cash = (cash_on_hand / monthly_expense_avg * 30) if monthly_expense_avg else 0
    program_ratio = abs(expense_df["Amount"].sum()) / abs(df["Amount"].sum()) if not df.empty else 0
    st.metric("💵 Days Cash on Hand", f"{days_cash:,.1f}")
    st.metric("📊 Program Expense Ratio", f"{program_ratio:.2%}")

    # --- Alerts ---
    st.subheader("🔔 Alerts")
    cash_threshold = st.number_input("Set Minimum Cash Threshold", value=5000)
    alert_message = f"⚠️ Cash on hand (${cash_on_hand:,.2f}) is below the threshold (${cash_threshold})" if cash_on_hand < cash_threshold else "✅ Cash on hand is healthy."
    st.info(alert_message)

    # --- Scenario Modeling ---
    st.subheader("🔄 Scenario Modeling")
    donation_increase = st.slider("Increase Donations by (%)", -50, 100, 0)
    expense_reduction = st.slider("Reduce Expenses by (%)", 0, 50, 0)
    scenario_income = income * (1 + donation_increase / 100)
    scenario_expense = expenses * (1 - expense_reduction / 100)
    scenario_net = scenario_income + scenario_expense
    st.write(f"📈 Scenario Net Cash Flow: ${scenario_net:,.2f}")

    # --- Multi-Year Comparison ---
    st.subheader("📆 Multi-Year Comparison")
    if df["Date"].dt.year.nunique() > 1:
        multi_year = df.groupby(df["Date"].dt.year)["Amount"].sum()
        st.bar_chart(multi_year)
        fig9, ax9 = plt.subplots()
        multi_year.plot(kind="bar", ax=ax9)
        ax9.set_title("Multi-Year Comparison")
        fig9.tight_layout()
        multiyear_path = os.path.join(chart_dir, "multi_year_comparison.png")
        fig9.savefig(multiyear_path)
        chart_files.append(multiyear_path)

    # --- EMAIL REPORT BUTTON ---
    st.subheader("📧 Send Full PDF Report")
    if st.button("Send PDF Report"):
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(200, 10, f"FundSight Summary Report - {selected_client}", ln=True)

            pdf.set_font("Arial", size=12)
            pdf.ln(8)
            pdf.cell(200, 10, f"Total Income: ${income:,.2f}", ln=True)
            pdf.cell(200, 10, f"Total Expenses: ${expenses:,.2f}", ln=True)
            pdf.cell(200, 10, f"Net Cash Flow: ${net:,.2f}", ln=True)
            pdf.cell(200, 10, f"Days Cash on Hand: {days_cash:.1f}", ln=True)
            pdf.cell(200, 10, f"Program Expense Ratio: {program_ratio:.2%}", ln=True)
            pdf.ln(10)
            for chart in chart_files:
                pdf.image(chart, w=180)
                pdf.ln(10)

            pdf_path = "/tmp/fundsight_full_report.pdf"
            pdf.output(pdf_path)

            # Email setup
            sender_email = st.secrets["email_user"]
            sender_password = st.secrets["email_password"]
            msg = MIMEMultipart()
            msg["From"] = sender_email
            msg["To"] = "jacob.b.franco@gmail.com"
            msg["Subject"] = f"FundSight Full Dashboard Report - {selected_client}"
            msg.attach(MIMEText("Attached is the full dashboard PDF report for your review.", "plain"))

            with open(pdf_path, "rb") as f:
                attachment = MIMEText(f.read(), "base64", "utf-8")
                attachment.add_header("Content-Disposition", "attachment", filename="fundsight_full_report.pdf")
                msg.attach(attachment)

            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(msg["From"], msg["To"], msg.as_string())
            server.quit()

            st.success("✅ Full PDF Report sent successfully!")

        except Exception as e:
            st.error(f"❌ Failed to send report: {e}")

else:
    st.info("📤 Please upload a QuickBooks CSV file to get started.")
