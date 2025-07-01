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
client_names = ["Client A", "Client B", "Client C"]
selected_client = st.sidebar.selectbox("Select Client", client_names)

# --- FILE UPLOADS ---
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
    fig1.savefig("/tmp/daily_cash_flow.png")

    # Expenses by Category
    st.subheader("📊 Expenses by Account Category")
    expense_df = df[df["Amount"] < 0]
    by_category = expense_df.groupby("Account")["Amount"].sum().sort_values()
    fig2, ax2 = plt.subplots()
    by_category.abs().plot(kind='barh', ax=ax2)
    ax2.set_title("Expenses by Category")
    fig2.tight_layout()
    st.pyplot(fig2)
    fig2.savefig("/tmp/expense_bar_chart.png")

    # Pie Chart
    st.subheader("🧁 Expense Distribution")
    fig3, ax3 = plt.subplots()
    ax3.pie(by_category.abs(), labels=by_category.index, autopct="%1.1f%%", startangle=90)
    ax3.axis("equal")
    st.pyplot(fig3)
    fig3.savefig("/tmp/expense_pie_chart.png")

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
    fig4.savefig("/tmp/forecast_chart.png")

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
            fig5, ax5 = plt.subplots()
            comparison.set_index("Account")[["Budget Amount", "Actual"]].abs().plot(kind='bar', ax=ax5)
            ax5.set_title("Budget vs Actuals")
            fig5.tight_layout()
            st.pyplot(fig5)
            fig5.savefig("/tmp/budget_vs_actuals.png")

    # Trend Analysis
    st.subheader("📉 Trend Analysis")
    monthly_trend = df.groupby(df["Date"].dt.to_period("M"))["Amount"].sum().reset_index()
    monthly_trend["Date"] = monthly_trend["Date"].astype(str)
    fig6, ax6 = plt.subplots()
    ax6.plot(monthly_trend["Date"], monthly_trend["Amount"])
    ax6.set_title("Monthly Trend")
    ax6.tick_params(axis='x', rotation=45)
    fig6.tight_layout()
    st.pyplot(fig6)
    fig6.savefig("/tmp/monthly_trend.png")

    # Top Revenue Sources
    if "Name" in df.columns:
        st.subheader("💌 Top Revenue Sources")
        top_sources = df[df["Amount"] > 0].groupby("Name")["Amount"].sum().sort_values(ascending=False).head(10)
        fig7, ax7 = plt.subplots()
        top_sources.plot(kind="bar", ax=ax7)
        ax7.set_title("Top Revenue Sources")
        fig7.tight_layout()
        st.pyplot(fig7)
        fig7.savefig("/tmp/top_sources.png")

    # Monthly Drill-down
    st.subheader("🔍 Monthly Expense Drill-down")
    monthly_expense = expense_df.groupby([df["Date"].dt.to_period("M"), "Account"])["Amount"].sum().unstack().fillna(0)
    fig8, ax8 = plt.subplots()
    monthly_expense.abs().plot(ax=ax8)
    ax8.set_title("Monthly Expense Drill-down")
    fig8.tight_layout()
    st.pyplot(fig8)
    fig8.savefig("/tmp/monthly_expense_drilldown.png")

    # Financial Ratios
    st.subheader("📊 Key Financial Ratios")
    monthly_avg_expense = abs(df[df["Amount"] < 0].set_index("Date")["Amount"].resample("M").sum().mean())
    days_cash = (cash_on_hand / monthly_avg_expense * 30) if monthly_avg_expense else 0
    program_ratio = abs(expense_df["Amount"].sum()) / abs(df["Amount"].sum()) if not df.empty else 0
    st.metric("💵 Days Cash on Hand", f"{days_cash:,.1f}")
    st.metric("📊 Program Expense Ratio", f"{program_ratio:.2%}")

    # Alerts
    st.subheader("🔔 Alerts")
    cash_threshold = st.number_input("Minimum Cash Threshold", value=5000)
    if cash_on_hand < cash_threshold:
        st.error("⚠️ Alert: Cash on hand is below threshold.")
    else:
        st.success("✅ Cash on hand is sufficient.")

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

    # Email PDF Report
    st.subheader("📧 Send Full Report as PDF")
    if st.button("Send PDF Report"):
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, f"FundSight Financial Summary - {selected_client}", ln=True)
            pdf.ln(10)
            pdf.multi_cell(0, 10, f"""
Total Income: ${income:,.2f}
Total Expenses: ${expenses:,.2f}
Net Cash Flow: ${net:,.2f}
Days Cash on Hand: {days_cash:.1f}
Program Expense Ratio: {program_ratio:.2%}
Projected Scenario Cash Flow: ${scenario_net:,.2f}
""")

            for chart in [
                "/tmp/daily_cash_flow.png", "/tmp/expense_bar_chart.png",
                "/tmp/expense_pie_chart.png", "/tmp/forecast_chart.png",
                "/tmp/budget_vs_actuals.png", "/tmp/monthly_trend.png",
                "/tmp/top_sources.png", "/tmp/monthly_expense_drilldown.png"
            ]:
                if os.path.exists(chart):
                    pdf.add_page()
                    pdf.image(chart, x=10, w=190)

            pdf_path = "/tmp/fundsight_report.pdf"
            pdf.output(pdf_path)

            # Summary for Email
            email_summary = f"""Hello,

Attached is the FundSight dashboard report for {selected_client}.

📊 Summary:
• Total Income: ${income:,.2f}
• Total Expenses: ${expenses:,.2f}
• Net Cash Flow: ${net:,.2f}
• Days Cash on Hand: {days_cash:.1f}
• Program Expense Ratio: {program_ratio:.2%}
• Scenario Net Cash Flow: ${scenario_net:,.2f}

Best regards,
FundSight Automated Reporting
"""

            # Email setup
            msg = MIMEMultipart()
            msg["From"] = st.secrets["email_user"]
            msg["To"] = "jacob.b.franco@gmail.com"
            msg["Subject"] = f"FundSight Report – {selected_client}"
            msg.attach(MIMEText(email_summary, "plain"))

            with open(pdf_path, "rb") as f:
                attach = MIMEApplication(f.read(), _subtype="pdf")
                attach.add_header("Content-Disposition", "attachment", filename="fundsight_report.pdf")
                msg.attach(attach)

            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(st.secrets["email_user"], st.secrets["email_password"])
            server.sendmail(msg["From"], msg["To"], msg.as_string())
            server.quit()

            st.success("✅ Report with summary sent via email!")
        except Exception as e:
            st.error(f"❌ Error sending report: {e}")

else:
    st.info("📤 Please upload a QuickBooks CSV file to get started.")

