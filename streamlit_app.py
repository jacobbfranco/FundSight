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

# 👉 Currency Formatter
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
