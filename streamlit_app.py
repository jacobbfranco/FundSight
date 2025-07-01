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

    chart_paths = []

    def save_chart(fig, filename):
        path = f"/tmp/{filename}.png"
        fig.savefig(path)
        chart_paths.append(path)
        plt.close(fig)

    # 📈 Daily Cash Flow Trend
    st.subheader("📈 Daily Cash Flow Trend")
    daily_totals = df.groupby("Date")["Amount"].sum().reset_index()
    fig, ax = plt.subplots()
    ax.plot(daily_totals["Date"], daily_totals["Amount"])
    ax.set_title("Daily Cash Flow")
    save_chart(fig, "daily_cash_flow")
    st.pyplot(fig)

    # 📊 Expenses by Account Category
    st.subheader("📊 Expenses by Account Category")
    expense_df = df[df["Amount"] < 0]
    by_category = expense_df.groupby("Account")["Amount"].sum().sort_values()
    fig, ax = plt.subplots()
    by_category.abs().plot(kind="barh", ax=ax)
    ax.set_title("Expenses by Account")
    save_chart(fig, "expenses_by_account")
    st.pyplot(fig)

    # 🧁 Expense Distribution
    st.subheader("🧁 Expense Distribution")
    fig, ax = plt.subplots()
    ax.pie(by_category.abs(), labels=by_category.index, autopct="%1.1f%%", startangle=90)
    ax.axis("equal")
    ax.set_title("Expense Distribution")
    save_chart(fig, "expense_pie")
    st.pyplot(fig)

    # 📅 30-Day Forecast
    st.subheader("📅 30-Day Cash Flow Projection")
    daily_avg = daily_totals["Amount"].mean()
    forecast_df = pd.DataFrame({
        "Date": pd.date_range(daily_totals["Date"].max() + timedelta(days=1), periods=30),
        "Amount": daily_avg
    })
    fig, ax = plt.subplots()
    ax.plot(forecast_df["Date"], forecast_df["Amount"])
    ax.set_title("30-Day Cash Flow Forecast")
    save_chart(fig, "forecast")
    st.pyplot(fig)

    # 📋 Budget vs Actuals
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
            fig, ax = plt.subplots()
            comparison.set_index("Account")[["Budget Amount", "Actual"]].abs().plot(kind="bar", ax=ax)
            ax.set_title("Budget vs Actuals")
            save_chart(fig, "budget_vs_actuals")
            st.pyplot(fig)

    # 📉 Trend Analysis
    st.subheader("📉 Trend Analysis")
    monthly_trend = df.groupby(df["Date"].dt.to_period("M"))["Amount"].sum().reset_index()
    monthly_trend["Date"] = monthly_trend["Date"].astype(str)
    fig, ax = plt.subplots()
    ax.plot(monthly_trend["Date"], monthly_trend["Amount"])
    ax.set_title("Monthly Trend")
    save_chart(fig, "trend_analysis")
    st.pyplot(fig)

    # 💌 Top Revenue Sources
    if "Name" in df.columns:
        st.subheader("💌 Top Revenue Sources")
        top_sources = df[df["Amount"] > 0].groupby("Name")["Amount"].sum().sort_values(ascending=False).head(10)
        fig, ax = plt.subplots()
        top_sources.plot(kind="bar", ax=ax)
        ax.set_title("Top Revenue Sources")
        save_chart(fig, "top_revenue_sources")
        st.pyplot(fig)

    # 🔍 Monthly Expense Drill-down
    st.subheader("🔍 Monthly Expense Drill-down")
    monthly_expense = expense_df.groupby([df["Date"].dt.to_period("M"), "Account"])["Amount"].sum().unstack().fillna(0)
    fig, ax = plt.subplots()
    monthly_expense.abs().plot(ax=ax)
    ax.set_title("Monthly Expense Drill-down")
    save_chart(fig, "monthly_drill")
    st.pyplot(fig)

    # 📊 Key Financial Ratios
    st.subheader("📊 Key Financial Ratios")
    monthly_avg_expense = abs(df[df["Amount"] < 0].set_index("Date")["Amount"].resample("M").sum().mean())
    days_cash = (cash_on_hand / monthly_avg_expense * 30) if monthly_avg_expense else 0
    program_ratio = abs(expense_df["Amount"].sum()) / abs(df["Amount"].sum()) if not df.empty else 0
    st.metric("💵 Days Cash on Hand", f"{days_cash:,.1f}")
    st.metric("📊 Program Expense Ratio", f"{program_ratio:.2%}")

    # 🔄 Scenario Modeling
    st.subheader("🔄 Scenario Modeling")
    donation_increase = st.slider("Donation Increase (%)", -50, 100, 0)
    expense_reduction = st.slider("Expense Reduction (%)", 0, 50, 0)
    scenario_income = income * (1 + donation_increase / 100)
    scenario_expense = expenses * (1 - expense_reduction / 100)
    scenario_net = scenario_income + scenario_expense
    st.write(f"📈 Projected Net Cash Flow: ${scenario_net:,.2f}")

    # 📆 Multi-Year Comparison
    st.subheader("📆 Multi-Year Comparison")
    if df["Date"].dt.year.nunique() > 1:
        fig, ax = plt.subplots()
        df.groupby(df["Date"].dt.year)["Amount"].sum().plot(kind="bar", ax=ax)
        ax.set_title("Multi-Year Comparison")
        save_chart(fig, "multi_year")
        st.pyplot(fig)

    # 📧 Send PDF Report
    st.subheader("📧 Send Full Report as PDF")
    if st.button("Send PDF Report"):
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.multi_cell(0, 10, f"FundSight Dashboard – {selected_client}", align="C")
            pdf.ln(5)
            summary_text = (
                f"Total Income: ${income:,.2f}\n"
                f"Total Expenses: ${expenses:,.2f}\n"
                f"Net Cash Flow: ${net:,.2f}\n"
                f"Days Cash on Hand: {days_cash:.1f}\n"
                f"Program Expense Ratio: {program_ratio:.2%}\n"
                f"Projected Net Cash Flow: ${scenario_net:,.2f}\n"
            )
            pdf.multi_cell(0, 10, summary_text)

            for chart_path in chart_paths:
                pdf.add_page()
                pdf.image(chart_path, x=10, w=190)

            pdf_path = "/tmp/fundsight_report.pdf"
            pdf.output(pdf_path)

            # Email it
            msg = MIMEMultipart()
            msg["From"] = st.secrets["email_user"]
            msg["To"] = "jacob.b.franco@gmail.com"
            msg["Subject"] = f"FundSight Dashboard Report – {selected_client}"
            msg.attach(MIMEText("Attached is your full dashboard report from FundSight."))

            with open(pdf_path, "rb") as f:
                attach = MIMEApplication(f.read(), _subtype="pdf")
                attach.add_header("Content-Disposition", "attachment", filename="fundsight_report.pdf")
                msg.attach(attach)

            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(st.secrets["email_user"], st.secrets["email_password"])
            server.sendmail(msg["From"], msg["To"], msg.as_string())
            server.quit()

            st.success("✅ Report sent via email!")
        except Exception as e:
            st.error(f"❌ Error sending report: {e}")

else:
    st.info("📤 Please upload a QuickBooks CSV file to get started.")

