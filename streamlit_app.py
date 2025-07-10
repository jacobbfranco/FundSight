import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import timedelta
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
import os
import json

# --- Helper Functions ---
def format_currency(value):
    return f"${value:,.2f}" if value >= 0 else f"(${abs(value):,.2f})"

def styled_metric(icon, label, value):
    return f"""
    <div style='background-color:#f9f9f9; padding:20px; border-radius:15px; box-shadow:2px 2px 10px rgba(0,0,0,0.1); text-align:center'>
        <div style='font-size:32px'>{icon}</div>
        <div style='font-size:18px; font-weight:bold; margin-top:5px'>{label}</div>
        <div style='font-size:24px; color:#2e8b57; margin-top:5px'>{value}</div>
    </div>
    """

# --- Page Config ---
st.set_page_config(page_title="FundSight Dashboard", layout="wide", page_icon="📊")

# --- Header ---
st.markdown("<h1 style='text-align:center;'>📊 FundSight: Nonprofit Finance Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align:center; color:gray;'>Financial clarity and insight for mission-driven leaders</h4>", unsafe_allow_html=True)
st.markdown("<hr style='margin-top:10px; margin-bottom:30px;'>", unsafe_allow_html=True)

# --- Sidebar Uploads ---
st.sidebar.header("📁 Upload Files")
uploaded_file = st.sidebar.file_uploader("Upload QuickBooks CSV", type=["csv"])
budget_file = st.sidebar.file_uploader("Upload Budget CSV (optional)", type=["csv"])
tag_file = st.sidebar.file_uploader("Upload Tag CSV (optional)", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
    df.dropna(subset=["Date"], inplace=True)
    
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
    df.dropna(subset=["Amount"], inplace=True)

    # --- Basic Metrics ---
    total_income = df[df["Amount"] > 0]["Amount"].sum()
    total_expense = df[df["Amount"] < 0]["Amount"].sum()
    net_cash_flow = total_income + total_expense

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(styled_metric("🟢", "Total Income", format_currency(total_income)), unsafe_allow_html=True)
    with col2:
        st.markdown(styled_metric("🔴", "Total Expenses", format_currency(total_expense)), unsafe_allow_html=True)
    with col3:
        st.markdown(styled_metric("💰", "Net Cash Flow", format_currency(net_cash_flow)), unsafe_allow_html=True)

    st.markdown("<hr style='margin-top:30px; margin-bottom:30px;'>", unsafe_allow_html=True)

    # --- Monthly Cash Flow Chart ---
    st.subheader("📅 Monthly Cash Flow Trend")
    df["Month"] = df["Date"].dt.to_period("M")
    monthly_cash = df.groupby("Month")["Amount"].sum()
    fig, ax = plt.subplots()
    monthly_cash.plot(kind="bar", ax=ax)
    ax.set_ylabel("Amount ($)")
    ax.set_title("Net Cash Flow by Month")
    st.pyplot(fig)

    st.markdown("<hr style='margin-top:30px; margin-bottom:30px;'>", unsafe_allow_html=True)

    # --- Expense by Category ---
    st.subheader("📂 Expenses by Category")
    expense_df = df[df["Amount"] < 0].copy()
    if "Account" in expense_df.columns:
        cat_expense = expense_df.groupby("Account")["Amount"].sum()
        cat_expense = cat_expense.sort_values()
        fig2, ax2 = plt.subplots()
        cat_expense.plot(kind="barh", ax=ax2)
        ax2.set_title("Expenses by Account")
        st.pyplot(fig2)

    st.markdown("<hr style='margin-top:30px; margin-bottom:30px;'>", unsafe_allow_html=True)

    # --- Tagging System ---
    if tag_file is not None:
        tag_df = pd.read_csv(tag_file)
        st.subheader("🏷️ Custom Transaction Tags")
        st.dataframe(tag_df)

    # --- Scenario Modeling Placeholder ---
    st.markdown("🧮 <b>Scenario Modeling</b>", unsafe_allow_html=True)
    st.markdown("<div style='padding:15px; background-color:#f0f2f6; border-radius:10px'>Add future-looking budget changes and visualize their impact.</div>", unsafe_allow_html=True)

    # --- Ratios Placeholder ---
    st.markdown("<hr style='margin-top:30px; margin-bottom:30px;'>", unsafe_allow_html=True)
    st.markdown("📊 <b>Financial Ratios</b>", unsafe_allow_html=True)
    st.markdown("<div style='padding:15px; background-color:#f0f2f6; border-radius:10px'>Coming soon: program % vs admin %, liquidity ratio, etc.</div>", unsafe_allow_html=True)

    # --- Board Notes Section ---
    st.markdown("<hr style='margin-top:30px; margin-bottom:30px;'>", unsafe_allow_html=True)
    board_notes = st.text_area("📝 Board Notes (optional)", "Enter any notes you'd like to appear in the board PDF...")

    # --- PDF/Email Placeholder ---
    st.markdown("<hr style='margin-top:30px; margin-bottom:30px;'>", unsafe_allow_html=True)
    st.markdown("📤 <b>PDF + Email</b>", unsafe_allow_html=True)
    st.markdown("<div style='padding:15px; background-color:#f0f2f6; border-radius:10px'>Coming soon: send this dashboard as a report.</div>", unsafe_allow_html=True)

else:
    st.info("Please upload a QuickBooks CSV to begin.")
