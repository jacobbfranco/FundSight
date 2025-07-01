import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fpdf import FPDF
import os

st.set_page_config(page_title="FundSight: Nonprofit Finance Dashboard", layout="wide")
st.title("📊 FundSight: QuickBooks Dashboard for Nonprofits")

# --- CLIENT SELECTION ---
st.sidebar.header("Client Selection")
client_names = ["Client A", "Client B", "Client C"]
selected_client = st.sidebar.selectbox("Select Client", client_names)

# --- FILE UPLOADS ---
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

    st.markdown(f"## Dashboard: {selected_client}")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Income", f"${income:,.2f}")
    col2.metric("Total Expenses", f"${expenses:,.2f}")
    col3.metric("Net Cash Flow", f"${net:,.2f}")
    st.markdown("---")

    # DAILY CASH FLOW
    st.subheader("Daily Cash Flow Trend")
    daily_totals = df.groupby("Date")["Amount"].sum().reset_index()
    fig1, ax1 = plt.subplots()
    ax1.plot(daily_totals["Date"], daily_totals["Amount"])
    ax1.set_title("Daily Cash Flow")
    ax1.set_xlabel("Date")
    ax1.set_ylabel("Amount")
    fig1.autofmt_xdate()
    st.pyplot(fig1)

    # EXPENSES BY CATEGORY
    st.subheader("Expenses by Account Category")
    expense_df = df[df["Amount"] < 0]
    by_category = expense_df.groupby("Account")["Amount"].sum().sort_values()
    fig2, ax2 = plt.subplots()
    by_category.abs().plot(kind="barh", ax=ax2)
    ax2.set_title("Expenses by Category")
    st.pyplot(fig2)

    # PIE CHART
    st.subheader("Expense Distribution")
    fig3, ax3 = plt.subplots()
    ax3.pie(by_category.abs(), labels=by_category.index, autopct="%1.1f%%", startangle=90)
    ax3.axis("equal")
    st.pyplot(fig3)

    # FORECAST
    st.subheader("30-Day Cash Flow Projection")
    daily_avg = daily_totals["Amount"].mean()
    future_dates = pd.date_range(start=daily_totals["Date"].max() + timedelta(days=1), periods=30)
    forecast_df = pd.DataFrame({"Date": future_dates, "Amount": daily_avg})
    fig4, ax4 = plt.subplots()
    ax4.plot(forecast_df["Date"], forecast_df["Amount"])
    ax4.set_title("30-Day Forecast")
    st.pyplot(fig4)

    # BUDGET VS ACTUALS
    if budget_file is not None:
        st.subheader("Budget vs Actuals")
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
            comparison[["Budget Amount", "Actual"]].abs().plot(kind="bar", ax=ax5)
            ax5.set_title("Budget vs Actuals")
            st.pyplot(fig5)

    # TREND ANALYSIS
    st.subheader("Trend Analysis")
    monthly_trend = df.groupby(df["Date"].dt.to_period("M"))["Amount"].sum().reset_index()
    monthly_trend["Date"] = monthly_trend["Date"].astype(str)
    fig6, ax6 = plt.subplots()
    ax6.plot(monthly_trend["Date"], monthly_trend["Amount"])
    ax6.set_title("Monthly Trend")
    st.pyplot(fig6)

    # TOP REVENUE SOURCES
    if "Name" in df.columns:
        st.subheader("Top Revenue Sources")
        top_sources = df[df["Amount"] > 0].groupby("Name")["Amount"].sum().sort_values(ascending=False).head(10)
        fig7, ax7 = plt.subplots()
        top_sources.plot(kind="bar", ax=ax7)
        ax7.set_title("Top Revenue Sources")
        st.pyplot(fig7)

    # MONTHLY EXPENSE DRILLDOWN
    st.subheader("Monthly Expense Drill-down")
    expense_by_month = expense_df.groupby([df["Date"].dt.to_period("M"), "Account"])["Amount"].sum().unstack().fillna(0)
    fig8, ax8 = plt.subplots()
    expense_by_month.abs().plot(ax=ax8)
    ax8.set_title("Monthly Expense by Account")
    st.pyplot(fig8)

    # KPIs
    st.subheader("Key Financial Ratios")
    monthly_expense_avg = abs(expense_df.set_index("Date")["Amount"].resample("M").sum().mean())
    days_cash = (df["Amount"].sum() / monthly_expense_avg * 30) if monthly_expense_avg else 0
    program_ratio = abs(expense_df["Amount"].sum()) / abs(df["Amount"].sum()) if not df.empty else 0
    st.metric("Days Cash on Hand", f"{days_cash:.1f}")
    st.metric("Program Expense Ratio", f"{program_ratio:.2%}")

    # ALERTS
    st.subheader("Alerts")
    threshold = st.number_input("Minimum Cash Threshold", value=5000)
    if df["Amount"].sum() < threshold:
        st.error("⚠️ Cash on hand is below threshold!")
    else:
        st.success("✅ Cash is above threshold.")

    # SCENARIO MODELING
    st.subheader("Scenario Modeling")
    donate_pct = st.slider("Increase Donations (%)", -50, 100, 0)
    expense_pct = st.slider("Reduce Expenses (%)", 0, 50, 0)
    scenario_income = income * (1 + donate_pct / 100)
    scenario_expense = expenses * (1 - expense_pct / 100)
    st.write(f"Projected Net Cash Flow: ${scenario_income + scenario_expense:,.2f}")

    # MULTI-YEAR
    if df["Date"].dt.year.nunique() > 1:
        st.subheader("Multi-Year Comparison")
        multiyear = df.groupby(df["Date"].dt.year)["Amount"].sum()
        fig9, ax9 = plt.subplots()
        multiyear.plot(kind="bar", ax=ax9)
        ax9.set_title("Multi-Year Comparison")
        st.pyplot(fig9)

    # GENERATE PDF & EMAIL
    st.subheader("📧 Send Full PDF Report")
    if st.button("Send PDF Report"):
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(200, 10, f"FundSight Summary – {selected_client}", ln=True)
            pdf.set_font("Arial", size=12)
            pdf.ln(5)
            pdf.cell(200, 10, f"Income: ${income:,.2f}", ln=True)
            pdf.cell(200, 10, f"Expenses: ${expenses:,.2f}", ln=True)
            pdf.cell(200, 10, f"Net Cash Flow: ${net:,.2f}", ln=True)
            pdf.cell(200, 10, f"Days Cash on Hand: {days_cash:.1f}", ln=True)
            pdf.cell(200, 10, f"Program Expense Ratio: {program_ratio:.2%}", ln=True)

            # Save and attach plots
            charts = [fig1, fig2, fig3, fig4, fig5 if budget_file else None, fig6, fig7, fig8, fig9 if df["Date"].dt.year.nunique() > 1 else None]
            y_offset = pdf.get_y() + 10
            for i, fig in enumerate(filter(None, charts)):
                path = f"/tmp/plot_{i}.png"
                fig.savefig(path, bbox_inches="tight")
                pdf.image(path, x=10, y=pdf.get_y() + 5, w=180)
                pdf.ln(85)

            pdf_path = "/tmp/fundsight_dashboard.pdf"
            pdf.output(pdf_path)

            # EMAIL
            sender_email = st.secrets["email_user"]
            sender_password = st.secrets["email_password"]
            msg = MIMEMultipart()
            msg["From"] = sender_email
            msg["To"] = "jacob.b.franco@gmail.com"
            msg["Subject"] = f"FundSight PDF Report – {selected_client}"

            email_text = f"""Attached is the FundSight PDF dashboard report for {selected_client}.

Net Cash Flow: ${net:,.2f}
Days Cash on Hand: {days_cash:.1f}
Program Expense Ratio: {program_ratio:.2%}
"""
            msg.attach(MIMEText(email_text, "plain"))

            with open(pdf_path, "rb") as f:
                part = MIMEText(f.read(), "base64", "utf-8")
                part.add_header("Content-Disposition", "attachment", filename="fundsight_dashboard.pdf")
                msg.attach(part)

            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(msg["From"], msg["To"], msg.as_string())
            server.quit()

            st.success("✅ PDF report emailed successfully.")
        except Exception as e:
            st.error(f"❌ Failed to send report: {e}")

else:
    st.info("Upload a QuickBooks CSV file to start.")
