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

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="FundSight: Nonprofit Finance Dashboard", layout="wide", page_icon="📊")
st.image("fundsight_logo.png", width=200)
st.title("📊 FundSight: QuickBooks Dashboard for Nonprofits")
st.markdown("Welcome to FundSight — a smarter way to manage nonprofit finances.")

# --- SIDEBAR: CLIENT + FILES ---
st.sidebar.header("👥 Client Selection")
client_names = ["Client A", "Client B", "Client C"]
selected_client = st.sidebar.selectbox("Select Client", client_names)

st.sidebar.markdown(f"### Upload files for {selected_client}")
uploaded_file = st.sidebar.file_uploader("Upload QuickBooks CSV", type=["csv"], key=f"{selected_client}_qb")
budget_file = st.sidebar.file_uploader("Upload Budget CSV (optional)", type=["csv"], key=f"{selected_client}_budget")
mortgage_file = st.sidebar.file_uploader("Upload Mortgage CSV", type=["csv"], key=f"{selected_client}_mortgage")

# --- MAIN DASHBOARD ---
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

    # Expense by Category
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

    # Forecasting
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

    # KPIs and Alerts
    st.subheader("📊 Key Financial Ratios & Alerts")
    monthly_avg_expense = abs(df[df["Amount"] < 0].set_index("Date")["Amount"].resample("M").sum().mean())
    days_cash = (cash_on_hand / monthly_avg_expense * 30) if monthly_avg_expense else 0
    program_ratio = abs(expense_df["Amount"].sum()) / abs(df["Amount"].sum()) if not df.empty else 0
    st.metric("💵 Days Cash on Hand", f"{days_cash:,.1f}")
    st.metric("📊 Program Expense Ratio", f"{program_ratio:.2%}")
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

    # PDF Report
    st.subheader("📧 Send Full Report as PDF")
    if st.button("Send PDF Report"):
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.image("fundsight_logo.png", x=10, w=50)
            pdf.cell(200, 10, f"FundSight Financial Summary - {selected_client}", ln=True)
            pdf.ln(10)
            pdf.multi_cell(0, 10, f'''
Total Income: ${income:,.2f}
Total Expenses: ${expenses:,.2f}
Net Cash Flow: ${net:,.2f}
Days Cash on Hand: {days_cash:.1f}
Program Expense Ratio: {program_ratio:.2%}
Projected Scenario Cash Flow: ${scenario_net:,.2f}
''')

            for chart in [
                "/tmp/daily_cash_flow.png", "/tmp/expense_bar_chart.png",
                "/tmp/expense_pie_chart.png", "/tmp/forecast_chart.png",
                "/tmp/budget_vs_actuals.png"
            ]:
                if os.path.exists(chart):
                    pdf.add_page()
                    pdf.image(chart, x=10, w=190)

            pdf_path = "/tmp/fundsight_report.pdf"
            pdf.output(pdf_path)

            msg = MIMEMultipart()
            msg["From"] = st.secrets["email_user"]
            msg["To"] = "jacob.b.franco@gmail.com"
            msg["Subject"] = f"FundSight Report – {selected_client}"
            msg.attach(MIMEText("Attached is your FundSight report.", "plain"))

            with open(pdf_path, "rb") as f:
                attach = MIMEApplication(f.read(), _subtype="pdf")
                attach.add_header("Content-Disposition", "attachment", filename="fundsight_report.pdf")
                msg.attach(attach)

            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(st.secrets["email_user"], st.secrets["email_password"])
            server.sendmail(msg["From"], msg["To"], msg.as_string())
            server.quit()

            st.success("✅ PDF report sent successfully!")
        except Exception as e:
            st.error(f"❌ Error sending PDF: {e}")

# Mortgage Tracking Module
if mortgage_file:
    st.subheader("🏠 Mortgage Tracker Module")
    mortgage_df = pd.read_csv(mortgage_file)
    st.dataframe(mortgage_df)

    if {"Amount Due", "Amount Paid", "Due Date"}.issubset(mortgage_df.columns):
        mortgage_df["Balance"] = mortgage_df["Amount Due"] - mortgage_df["Amount Paid"]
        mortgage_df["Due Date"] = pd.to_datetime(mortgage_df["Due Date"])
        mortgage_df["Days Late"] = (pd.Timestamp.now() - mortgage_df["Due Date"]).dt.days
        mortgage_df["Delinquent"] = mortgage_df["Days Late"] > 60

        # Charts
        st.markdown("### 📊 Current vs Delinquent Loans")
        delinquency_counts = mortgage_df["Delinquent"].value_counts()
        st.pyplot(plt.pie(delinquency_counts, labels=["Current", "Delinquent"], autopct="%1.1f%%")[0].figure)

        st.markdown("### 📉 Balances by Loan ID")
        st.bar_chart(mortgage_df.set_index("Loan ID")["Balance"])

        # Projected inflows
        inflow = mortgage_df[mortgage_df["Delinquent"] == False]["Amount Paid"].sum()
        st.metric("📆 Projected Monthly Repayments", f"${inflow:,.2f}")

        # Late table
        st.markdown("### 🚨 Delinquency Table")
        st.dataframe(mortgage_df[mortgage_df["Delinquent"] == True][["Borrower", "Loan ID", "Days Late", "Balance"]])




