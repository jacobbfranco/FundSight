import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import timedelta
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
import tempfile
import os

st.set_page_config(page_title="FundSight: Nonprofit Finance Dashboard", layout="wide")
st.title("📊 FundSight: QuickBooks Dashboard for Nonprofits")

# --- MULTI-CLIENT SUPPORT ---
st.sidebar.header("👥 Client Selection")
clients = ["Client A", "Client B", "Client C"]
selected_client = st.sidebar.selectbox("Select Client", clients)

# --- FILE UPLOAD ---
st.sidebar.markdown(f"### Upload files for {selected_client}")
uploaded_file = st.sidebar.file_uploader("Upload QuickBooks CSV", type=["csv"], key=f"{selected_client}_qb")
budget_file = st.sidebar.file_uploader("Upload Budget CSV (optional)", type=["csv"], key=f"{selected_client}_budget")

# --- PROCESSING ---
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Account"] = df["Account"].str.strip()
    if "Name" in df.columns:
        df["Name"] = df["Name"].fillna("Unknown")

    income = df[df["Amount"] > 0]["Amount"].sum()
    expenses = df[df["Amount"] < 0]["Amount"].sum()
    net = income + expenses
    st.metric("🟢 Total Income", f"${income:,.2f}")
    st.metric("🔴 Total Expenses", f"${expenses:,.2f}")
    st.metric("💰 Net Cash Flow", f"${net:,.2f}")

    # --- CHARTS TO ADD TO PDF ---
    charts = []

    def save_chart(fig, name):
        temp_path = os.path.join(tempfile.gettempdir(), f"{name}.png")
        fig.savefig(temp_path, bbox_inches='tight')
        charts.append(temp_path)

    # --- DAILY CASH FLOW ---
    st.subheader("📈 Daily Cash Flow Trend")
    daily_totals = df.groupby("Date")["Amount"].sum()
    fig, ax = plt.subplots()
    daily_totals.plot(ax=ax, title="Daily Cash Flow")
    st.pyplot(fig)
    save_chart(fig, "daily_cash_flow")

    # --- EXPENSES BY ACCOUNT ---
    st.subheader("📊 Expenses by Account Category")
    expense_df = df[df["Amount"] < 0]
    by_category = expense_df.groupby("Account")["Amount"].sum().sort_values()
    fig, ax = plt.subplots(figsize=(10, 6))
    by_category.abs().plot(kind="barh", ax=ax, title="Expenses by Account")
    ax.set_xlabel("Amount")
    st.pyplot(fig)
    save_chart(fig, "expenses_by_account")

    # --- EXPENSE PIE ---
    st.subheader("🧁 Expense Distribution")
    fig, ax = plt.subplots()
    ax.pie(by_category.abs(), labels=by_category.index, autopct="%1.1f%%", startangle=90)
    ax.axis("equal")
    st.pyplot(fig)
    save_chart(fig, "expense_distribution")

    # --- FORECAST ---
    st.subheader("📅 30-Day Cash Flow Forecast")
    daily_avg = daily_totals.mean()
    future_dates = pd.date_range(start=daily_totals.index.max() + timedelta(days=1), periods=30)
    forecast_df = pd.DataFrame({"Date": future_dates, "Amount": daily_avg})
    fig, ax = plt.subplots()
    forecast_df.set_index("Date").plot(ax=ax, title="30-Day Cash Flow Forecast")
    st.pyplot(fig)
    save_chart(fig, "cash_flow_forecast")

    # --- BUDGET VS ACTUAL ---
    if budget_file is not None:
        budget_df = pd.read_csv(budget_file)
        budget_df.columns = budget_df.columns.str.strip()
        budget_df["Account"] = budget_df["Account"].str.strip()
        actuals = df.groupby("Account")["Amount"].sum()
        comparison = pd.merge(budget_df, actuals.rename("Actual"), on="Account", how="outer").fillna(0)
        comparison["Variance"] = comparison["Actual"] - comparison["Budget Amount"]
        st.subheader("📋 Budget vs Actuals")
        st.dataframe(comparison)
        fig, ax = plt.subplots(figsize=(10, 6))
        comparison.set_index("Account")[["Budget Amount", "Actual"]].abs().plot(kind="bar", ax=ax, title="Budget vs Actuals")
        st.pyplot(fig)
        save_chart(fig, "budget_vs_actuals")

    # --- REVENUE SOURCES ---
    if "Name" in df.columns:
        top_sources = df[df["Amount"] > 0].groupby("Name")["Amount"].sum().nlargest(10)
        st.subheader("💌 Top Revenue Sources")
        fig, ax = plt.subplots()
        top_sources.plot(kind="bar", ax=ax, title="Top Revenue Sources")
        st.pyplot(fig)
        save_chart(fig, "top_revenue_sources")

    # --- MULTI-YEAR COMPARISON ---
    st.subheader("📆 Multi-Year Comparison")
    df["Year"] = df["Date"].dt.year
    if df["Year"].nunique() > 1:
        multi_year = df.groupby("Year")["Amount"].sum()
        fig, ax = plt.subplots()
        multi_year.plot(kind="bar", ax=ax, title="Multi-Year Totals")
        st.pyplot(fig)
        save_chart(fig, "multi_year_comparison")

    # --- PDF GENERATION ---
    st.subheader("📧 Send PDF Report via Email")

    if st.button("Send Report"):
        try:
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, f"FundSight Report - {selected_client}", ln=True)
            pdf.ln(10)
            pdf.set_font("Arial", "", 12)
            pdf.multi_cell(0, 10, f"Net Cash Flow: ${net:,.2f}\n\n")

            for chart_path in charts:
                pdf.add_page()
                pdf.image(chart_path, x=10, w=190)

            temp_pdf = os.path.join(tempfile.gettempdir(), f"{selected_client}_fundsight_report.pdf")
            pdf.output(temp_pdf)

            msg = MIMEMultipart()
            msg["From"] = st.secrets["email_user"]
            msg["To"] = "jacob.b.franco@gmail.com"
            msg["Subject"] = f"FundSight Dashboard Report - {selected_client}"
            msg.attach(MIMEText("Attached is your FundSight dashboard PDF report.", "plain"))

            with open(temp_pdf, "rb") as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(temp_pdf))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(temp_pdf)}"'
                msg.attach(part)

            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(st.secrets["email_user"], st.secrets["email_password"])
                server.send_message(msg)

            st.success("✅ Report emailed successfully!")
        except Exception as e:
            st.error(f"❌ Failed to send email: {e}")

else:
    st.info("📤 Please upload a QuickBooks CSV file to get started.")
