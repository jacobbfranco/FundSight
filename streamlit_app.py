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

# 👉 Add this helper function here:
def format_currency(value):
    if value < 0:
        return f"(${abs(value):,.2f})"
    else:
        return f"${value:,.2f}"

# --- App Setup ---
st.set_page_config(page_title="FundSight Dashboard", layout="wide", page_icon="📊")
st.image("fundsight_logo.png", width=200)

# --- Sidebar ---
st.sidebar.header("👥 Client Selection")
clients = ["Client A", "Client B", "Client C"]
selected_client = st.sidebar.selectbox("Select Client", clients)

uploaded_file = st.sidebar.file_uploader("Upload QuickBooks CSV", type="csv")
budget_file = st.sidebar.file_uploader("Upload Budget CSV (optional)", type="csv")
mortgage_file = st.sidebar.file_uploader("Upload Mortgage CSV (optional)", type="csv")

include_signature = st.sidebar.checkbox("🖋 Include Signature Section")
show_email_button = st.sidebar.checkbox("📤 Enable Email to Board")

# --- Main Heading ---
st.markdown(f"""
## FundSight Dashboard for {selected_client}  
<span style='font-size:16px; color:gray;'>Built for Nonprofits • Financial Clarity at a Glance</span>
""", unsafe_allow_html=True)

# --- Load & Process QuickBooks CSV ---
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
    col2.metric("🔴 Total Expenses", f"(${abs(expenses):,.2f})")
    col3.metric("💰 Net Cash Flow", f"${net:,.2f}")
    st.markdown("---")

    # --- Scenario Modeling (v2) ---
    st.subheader("🔄 Scenario Modeling")

    donation_increase = st.slider("📈 Donation Increase (%)", -50, 100, 0)
    grant_change = st.slider("🏛️ Grant Revenue Change (%)", -50, 100, 0)
    personnel_change = st.slider("👥 Personnel Expense Change (%)", -50, 50, 0)
    program_change = st.slider("🧱 Program Expense Change (%)", -50, 50, 0)
    unexpected_cost = st.number_input("⚠️ One-Time Unexpected Cost ($)", min_value=0, value=0, step=1000)

    personnel_expense = df[df["Account"].str.contains("Salary|Wages|Payroll", case=False, na=False)]["Amount"].sum()
    program_expense = df[df["Account"].str.contains("Program|Construction|Materials|Supplies", case=False, na=False)]["Amount"].sum()
    other_expense = expenses - (personnel_expense + program_expense)

    scenario_donation = income * (1 + donation_increase / 100)
    scenario_grant = income * (grant_change / 100)
    scenario_income = scenario_donation + scenario_grant

    adj_personnel = personnel_expense * (1 + personnel_change / 100)
    adj_program = program_expense * (1 + program_change / 100)

    scenario_expenses = adj_personnel + adj_program + other_expense + (-unexpected_cost)
    scenario_net = scenario_income + scenario_expenses

    st.markdown("### 📉 Projected Scenario Outcome")
    st.metric("📈 Adjusted Net Cash Flow", f"{format_currency(scenario_net)}")
    st.caption("This projection includes selected revenue and expense changes.")

    # --- Multi-Year Chart ---
    st.subheader("📆 Multi-Year Comparison")
    if df["Date"].dt.year.nunique() > 1:
        st.bar_chart(df.groupby(df["Date"].dt.year)["Amount"].sum())
         
