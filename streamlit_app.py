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
client_names = ["Client A", "Client B", "Client C", "Habitat for Humanity"]
selected_client = st.sidebar.selectbox("Select Client", client_names)

# --- FILE UPLOADS ---
st.sidebar.markdown(f"### Upload files for {selected_client}")
uploaded_file = st.sidebar.file_uploader("Upload QuickBooks CSV", type=["csv"], key=f"{selected_client}_qb")
budget_file = st.sidebar.file_uploader("Upload Budget CSV (optional)", type=["csv"], key=f"{selected_client}_budget")

# Optional modules toggles
st.sidebar.markdown("### Optional Modules")
show_mortgage = st.sidebar.checkbox("📋 Include Mortgage Tracking")
show_board_report = st.sidebar.checkbox("📩 Include Board Report Generator")

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

    if show_mortgage:
        st.subheader("🏠 Mortgage Tracking Module")
        st.markdown("Upload your mortgage CSV file (Borrower, Loan ID, Amount Due, Amount Paid, Due Date)")
        mortgage_file = st.sidebar.file_uploader("Upload Mortgage CSV", type=["csv"], key=f"{selected_client}_mortgage")
        if mortgage_file:
            mortgage_df = pd.read_csv(mortgage_file)
            mortgage_df["Balance"] = mortgage_df["Amount Due"] - mortgage_df["Amount Paid"]
            mortgage_df["Due Date"] = pd.to_datetime(mortgage_df["Due Date"])
            mortgage_df["Delinquent"] = (mortgage_df["Balance"] > 0) & (mortgage_df["Due Date"] < pd.Timestamp.today())
            st.write("📄 Mortgage Data Preview")
            st.dataframe(mortgage_df)

            st.markdown("### 📉 Mortgage Balances")
            fig, ax = plt.subplots()
            mortgage_df.set_index("Loan ID")["Balance"].plot(kind="bar", ax=ax)
            ax.set_title("Outstanding Mortgage Balances")
            st.pyplot(fig)

            delinquent_count = mortgage_df["Delinquent"].sum()
            st.metric("🚨 Delinquent Loans", int(delinquent_count))

    if show_board_report:
        st.subheader("📋 Board Reports")
        st.markdown("This section prepares and sends board-ready summaries.")
        board_email = st.text_input("📧 Board Email Address", "jacob.b.franco@gmail.com")
        pdf_path = "/tmp/fundsight_report.pdf"
        if st.button("Send Monthly Board Report"):
            try:
                msg = MIMEMultipart()
                msg["From"] = st.secrets["email_user"]
                msg["To"] = board_email
                msg["Subject"] = f"Monthly Board Report – {selected_client}"

                summary = f"""
Dear Board Member,

Attached is this month's FundSight financial overview for {selected_client}.

• Total Income: ${income:,.2f}
• Total Expenses: ${expenses:,.2f}
• Net Cash Flow: ${net:,.2f}
• Days Cash on Hand: N/A
• Program Expense Ratio: N/A

Warm regards,
FundSight Board Reporting Tool
"""
                msg.attach(MIMEText(summary, "plain"))
                if os.path.exists(pdf_path):
                    with open(pdf_path, "rb") as f:
                        attach = MIMEApplication(f.read(), _subtype="pdf")
                        attach.add_header("Content-Disposition", "attachment", filename="Board_Report.pdf")
                        msg.attach(attach)

                server = smtplib.SMTP("smtp.gmail.com", 587)
                server.starttls()
                server.login(st.secrets["email_user"], st.secrets["email_password"])
                server.sendmail(msg["From"], msg["To"], msg.as_string())
                server.quit()

                st.success("✅ Board Report sent successfully!")
            except Exception as e:
                st.error(f"❌ Error sending board report: {e}")

else:
    st.info("📤 Please upload a QuickBooks CSV file to get started.")



