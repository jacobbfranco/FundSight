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

# --- Custom PDF Class with Footer ---
from fpdf import FPDF
class FundSightPDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 10)
        self.set_text_color(100)
        self.cell(0, 10, "Built for Nonprofits - Financial Clarity at a Glance", 0, 0, "C")

# --- Formatting ---
def format_currency(value):
    if value < 0:
        return f"(${abs(value):,.2f})"
    return f"${value:,.2f}"

# --- Setup ---
st.set_page_config(page_title="FundSight Dashboard", layout="wide", page_icon="📊")
st.image("fundsight_logo.png", width=200)

# --- Sidebar ---
with st.sidebar:
    st.header("👥 Client Settings")
    clients = ["Client A", "Client B", "Client C"]
    selected_client = st.selectbox("Select Client", clients)

    st.markdown("#### Upload Files")

    # QuickBooks CSV Upload
    uploaded_file = st.file_uploader(
        "QuickBooks CSV",
        type="csv",
        help="Export from QuickBooks > Reports > Transactions"
    )
    if uploaded_file is None:
        st.caption("✅ Include columns like: Date, Account, Amount, Name")

    # Budget CSV Upload
    budget_file = st.file_uploader(
        "Budget CSV (optional)",
        type="csv",
        help="Compare actuals vs budget"
    )
    if budget_file is None:
        st.caption("✅ Include: Account, Budget Amount")

    # Mortgage CSV Upload
    mortgage_file = st.file_uploader(
        "Mortgage CSV (optional)",
        type="csv",
        help="Track loan balances and delinquencies"
    )
    if mortgage_file is None:
        st.caption("✅ Include: Borrower, Loan ID, Amount Due, Amount Paid, Due Date")

    st.markdown("#### Display Settings")
    include_signature = st.checkbox("🖋 Include Signature Section in PDF")
    show_email_button = st.checkbox("📤 Enable Email Report Button")

    st.markdown("---")
    st.header("🎯 Goals (Health Score)")
    goal_cash = st.number_input("Cash on Hand Goal ($)", value=10000)
    goal_income = st.number_input("Monthly Income Goal ($)", value=5000)
    goal_program_ratio = st.slider("Program Ratio Goal", 0.0, 1.0, 0.75)

# --- Header ---
st.markdown(f"""## FundSight Dashboard for **{selected_client}**
<small style='color: gray;'>Designed for Nonprofits • QuickBooks-Compatible</small>""", unsafe_allow_html=True)
st.markdown("---")

# File display message
if not uploaded_file:
    st.info("⬆️ Upload your QuickBooks CSV file to begin.")

# --- Load CSV + Process ---
if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)

        # Validate required columns
        required_cols = ["Date", "Account", "Amount"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            st.error(f"❌ Missing required columns: {', '.join(missing_cols)}")
        else:
            # Attempt to parse Date column
            try:
                df["Date"] = pd.to_datetime(df["Date"], errors="raise")
            except Exception as e:
                st.error("❌ Could not parse 'Date' column. Please check formatting (e.g. MM/DD/YYYY).")
                st.stop()

            # Clean and prep data
            df["Account"] = df["Account"].astype(str).str.strip()
            if "Name" in df.columns:
                df["Name"] = df["Name"].fillna("Unknown")

            # Now proceed as normal
            income = df[df["Amount"] > 0]["Amount"].sum()
            expenses = df[df["Amount"] < 0]["Amount"].sum()
            net = income + expenses
            cash_on_hand = df["Amount"].sum()

            # Display metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("🟢 Total Income", format_currency(income))
            col2.metric("🔴 Total Expenses", format_currency(expenses))
            col3.metric("💰 Net Cash Flow", format_currency(net))
            st.markdown("---")

            # (Continue with rest of dashboard logic...)
    
    except Exception as e:
        st.error(f"❌ Error loading file: {e}")
    
    # --- Scenario Modeling ---
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
    st.metric("📈 Adjusted Net Cash Flow", format_currency(scenario_net))

    # --- Multi-Year Chart ---
    if df["Date"].dt.year.nunique() > 1:
        st.subheader("📆 Multi-Year Comparison")
        st.bar_chart(df.groupby(df["Date"].dt.year)["Amount"].sum())

    # --- Ratios + Health Score ---
    st.subheader("📊 Key Financial Ratios")
    monthly_avg_expense = abs(df[df["Amount"] < 0].set_index("Date")["Amount"].resample("M").sum().mean())
    days_cash = (cash_on_hand / monthly_avg_expense * 30) if monthly_avg_expense else 0
    program_ratio = abs(program_expense) / abs(expenses) if expenses else 0
    st.metric("💵 Days Cash on Hand", f"{days_cash:,.1f}")
    st.metric("📊 Program Expense Ratio", f"{program_ratio:.2%}")

    # --- Health Score ---
    st.subheader("🧮 Client Health Score")
    cash_score = min(cash_on_hand / goal_cash, 1)
    income_score = min(income / goal_income, 1)
    ratio_score = min(program_ratio / goal_program_ratio, 1)
    health_score = round((cash_score + income_score + ratio_score) / 3, 2)
    health_color = "🟢" if health_score >= 0.8 else "🟡" if health_score >= 0.5 else "🔴"
    st.metric(f"{health_color} Health Score", f"{health_score:.2f}")

    # --- Alerts ---
    st.subheader("🔔 Alerts")
    threshold = st.number_input("Minimum Cash Threshold", value=5000, key="cash_threshold")
    if cash_on_hand < threshold:
        st.error("⚠️ Alert: Cash on hand is below minimum threshold.")
    else:
        st.success("✅ Cash on hand is sufficient.")

    expense_limit = st.number_input("📉 Maximum Total Expenses Allowed ($)", value=100000, key="expense_limit")
    if abs(expenses) > expense_limit:
        st.error(f"⚠️ Alert: Total expenses (${abs(expenses):,.2f}) exceed the limit.")
    else:
        st.success("✅ Expenses are within acceptable range.")

    min_program_ratio = st.slider("📊 Minimum Program Expense Ratio", 0.0, 1.0, 0.75, key="program_ratio_min")
    if program_ratio < min_program_ratio:
        st.error(f"⚠️ Alert: Program Ratio is below goal ({program_ratio:.2%} < {min_program_ratio:.0%})")
    else:
        st.success("✅ Program Ratio meets the target.")

# --- Grant Intelligence Module ---
st.subheader("🎓 Grant Intelligence Module")

grant_summary = ""
if uploaded_file is not None:
    grant_keywords = ["grant", "foundation", "fund", "award"]
    grant_df = df[df["Account"].str.contains("|".join(grant_keywords), case=False, na=False)]

    if not grant_df.empty:
        source_col = "Name" if "Name" in grant_df.columns else "Account"
        grant_by_source = grant_df.groupby(source_col)["Amount"].sum().sort_values(ascending=False)

        # Remove negative values (if any) for pie chart
        grant_by_source = grant_by_source[grant_by_source > 0]

        total_grants = grant_df["Amount"].sum()
        top_source = grant_by_source.idxmax() if not grant_by_source.empty else "N/A"
        top_amount = grant_by_source.max() if not grant_by_source.empty else 0

        st.metric("🎁 Total Grant Income", format_currency(total_grants))
        st.metric("🏆 Top Grant Source", f"{top_source} ({format_currency(top_amount)})")

        if not grant_by_source.empty:
            st.bar_chart(grant_by_source)

            fig, ax = plt.subplots()
            ax.pie(grant_by_source, labels=grant_by_source.index, autopct="%1.1f%%", startangle=90)
            ax.axis("equal")
            st.pyplot(fig)

        st.dataframe(grant_df)

        grant_summary = f"Total Grants: {format_currency(total_grants)}\nTop Source: {top_source} - {format_currency(top_amount)}"
    else:
        st.info("No grant-related transactions detected in this dataset.")
   
 # --- Budget vs Actuals ---
if budget_file:
    try:
        budget_df = pd.read_csv(budget_file)

        # Check for required columns
        required_budget_cols = ["Account", "Budget Amount"]
        missing_budget_cols = [col for col in required_budget_cols if col not in budget_df.columns]
        if missing_budget_cols:
            st.error(f"❌ Budget file is missing columns: {', '.join(missing_budget_cols)}")
        else:
            # Attach actuals
            if "Actual" not in budget_df.columns:
                actuals = df.groupby("Account")["Amount"].sum().reset_index()
                actuals.rename(columns={"Amount": "Actual"}, inplace=True)
                budget_df = pd.merge(budget_df, actuals, on="Account", how="left")

            # Calculate Variance
            budget_df["Variance"] = budget_df["Budget Amount"] - budget_df["Actual"]
            st.subheader("📊 Budget vs Actuals")
            st.dataframe(budget_df)

    except Exception as e:
        st.error(f"❌ Error reading budget file: {e}")
    
# --- Mortgage Tracker ---
if mortgage_file:
    try:
        mortgage_df = pd.read_csv(mortgage_file)
        required_mortgage_cols = ["Borrower", "Loan ID", "Amount Due", "Amount Paid", "Due Date"]
        missing_mortgage_cols = [col for col in required_mortgage_cols if col not in mortgage_df.columns]

        if missing_mortgage_cols:
            st.error(f"❌ Mortgage file is missing columns: {', '.join(missing_mortgage_cols)}")
        else:
            mortgage_df["Due Date"] = pd.to_datetime(mortgage_df["Due Date"], errors="coerce")
            mortgage_df["Balance"] = mortgage_df["Amount Due"] - mortgage_df["Amount Paid"]
            mortgage_df["Days Late"] = (pd.Timestamp.today() - mortgage_df["Due Date"]).dt.days
            mortgage_df["Delinquent"] = mortgage_df["Days Late"] > 60

            st.subheader("🏠 Mortgage Tracker")
            st.metric("Total Outstanding Balance", format_currency(mortgage_df["Balance"].sum()))
            st.metric("🚨 Delinquent Loans", mortgage_df["Delinquent"].sum())

            delinquency_counts = mortgage_df['Delinquent'].value_counts()
            values = [delinquency_counts.get(False, 0), delinquency_counts.get(True, 0)]
            labels = ["Current", "Delinquent"]

            fig, ax = plt.subplots()
            ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
            ax.axis("equal")
            st.pyplot(fig)

            st.bar_chart(mortgage_df.set_index("Loan ID")["Balance"])
            st.dataframe(mortgage_df)

    except Exception as e:
        st.error(f"❌ Error processing mortgage file: {e}")

# --- Form 990 Organizer & Prep Module ---
st.markdown("### 🧾 IRS Form 990 Organizer")
st.markdown("Use this section to organize key Form 990 details throughout the year.")

with st.expander("📌 Basic Organization Details"):
    org_name = st.text_input("Organization Name")
    ein = st.text_input("Employer Identification Number (EIN)")
    tax_year = st.text_input("Tax Year (e.g. 2024)")
    tax_preparer = st.text_input("Tax Preparer or Firm")

with st.expander("💼 Governance and Policies"):
    board_size = st.number_input("Number of Board Members", min_value=1, step=1)
    conflict_policy = st.radio("Conflict of Interest Policy in Place?", ["Yes", "No"])
    whistleblower_policy = st.radio("Whistleblower Policy?", ["Yes", "No"])
    document_retention = st.radio("Document Retention Policy?", ["Yes", "No"])

with st.expander("💸 Compensation & Fundraising"):
    ceo_name = st.text_input("CEO/Executive Director Name")
    ceo_comp = st.number_input("CEO Total Compensation", min_value=0, step=1000)
    fundraising_expense = st.number_input("Fundraising Expenses", min_value=0, step=1000)

with st.expander("📝 Program Services"):
    st.markdown("Describe your major program services and accomplishments:")
    program_1 = st.text_area("Program Service 1", height=100)
    program_2 = st.text_area("Program Service 2", height=100)
    program_3 = st.text_area("Program Service 3", height=100)

st.success("✅ You can come back and update these fields anytime. PDF export and email coming soon.")

# --- Board Notes ---
st.markdown("### 📝 Board Notes")
board_notes = st.text_area("Enter any notes you'd like to include in the Board PDF report:", height=150)

# --- PDF Class with Footer ---
class FundSightPDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 10)
        self.set_text_color(100)
        self.cell(0, 10, "Built for Nonprofits - Financial Clarity at a Glance", 0, 0, "C")

# --- PDF Section Selection Checkboxes ---
mortgage_summary = ""

if show_email_button and uploaded_file:
    st.markdown("### 🖍 Select Sections to Include in Board PDF")
    include_summary = st.checkbox("Include Financial Summary", value=True)
    include_ratios = st.checkbox("Include Financial Ratios", value=True)
    include_scenario = st.checkbox("Include Scenario Modeling", value=True)
    include_grants = st.checkbox("Include Grant Summary", value=bool(grant_summary))
    include_mortgage = st.checkbox("Include Mortgage Summary", value=bool(mortgage_file))
    include_chart = st.checkbox("Include Income vs Expense Chart", value=True)
    include_notes = st.checkbox("Include Board Notes", value=True)
    include_signature_block = st.checkbox("Include Signature Section", value=include_signature)

    recipient_email = st.text_input("Recipient Email", value=st.secrets["email"]["email_user"])
    custom_subject = st.text_input("Email Subject", value=f"Board Finance Report for {selected_client}")
    custom_body = st.text_area("Email Body", value="Attached is your FundSight Board Finance Report.")

    # --- Create Income vs Expenses Chart ---
    chart_path = "/tmp/income_expense_chart.png"
    if include_chart:
        try:
            fig, ax = plt.subplots()
            ax.bar(["Income", "Expenses"], [income, abs(expenses)], color=["green", "red"])
            ax.set_title("Income vs Expenses")
            ax.set_ylabel("Amount ($)")
            fig.tight_layout()
            fig.savefig(chart_path, bbox_inches="tight")
            plt.close(fig)
        except Exception as e:
            chart_path = ""
            st.warning(f"⚠️ Could not generate chart for PDF: {e}")

    st.markdown("### 📤 Send PDF Report")
    if st.button("Send PDF Report"):
        try:
            from datetime import datetime
            pdf = FundSightPDF()
            pdf.client_name = selected_client
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=20)

            # --- Header Section ---
            if os.path.exists("fundsight_logo.png"):
                pdf.image("fundsight_logo.png", x=10, y=10, w=25)

            pdf.set_xy(0, 10)
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Board Finance Report", border=0, ln=0, align="C")

            pdf.set_xy(-50, 10)
            pdf.set_font("Arial", "", 11)
            pdf.cell(40, 10, datetime.now().strftime("%b %d, %Y"), ln=0, align="R")

            pdf.set_xy(10, 20)
            pdf.set_font("Arial", "", 11)
            pdf.set_text_color(50)
            pdf.cell(0, 10, f"Client: {selected_client}", ln=True)

            pdf.set_draw_color(100)
            pdf.line(10, 28, 200, 28)
            pdf.ln(10)

            # --- PDF Sections ---
            if include_summary:
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 8, "Board Financial Summary", ln=True)
                pdf.set_font("Arial", "", 11)
                pdf.cell(0, 8, f"Total Income:           {format_currency(income)}", ln=True)
                pdf.cell(0, 8, f"Total Expenses:         {format_currency(expenses)}", ln=True)
                pdf.cell(0, 8, f"Net Cash Flow:          {format_currency(net)}", ln=True)
                pdf.ln(3)

            if include_ratios:
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 8, "Key Ratios", ln=True)
                pdf.set_font("Arial", "", 11)
                pdf.cell(0, 8, f"Days Cash on Hand: {days_cash:,.1f}", ln=True)
                pdf.cell(0, 8, f"Program Expense Ratio: {program_ratio:.2%}", ln=True)
                pdf.ln(3)

            if include_scenario:
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 8, "Scenario Modeling", ln=True)
                pdf.set_font("Arial", "", 11)
                pdf.cell(0, 8, f"Projected Net Cash Flow: {format_currency(scenario_net)}", ln=True)
                pdf.cell(0, 8, f"(Donation increase: {donation_increase:+}%, Grant change: {grant_change:+}%)", ln=True)
                pdf.ln(3)

            if include_grants and grant_summary:
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 8, "Grant Summary", ln=True)
                pdf.set_font("Arial", "", 11)
                for line in grant_summary.split("\\n"):
                    pdf.cell(0, 8, line, ln=True)
                pdf.ln(3)

            if include_mortgage and mortgage_summary:
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 8, "Mortgage Summary", ln=True)
                pdf.set_font("Arial", "", 11)
                for line in mortgage_summary.split("\\n"):
                    pdf.cell(0, 8, line, ln=True)
                pdf.ln(3)

            if include_chart and chart_path and os.path.exists(chart_path):
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 8, "Income vs Expenses", ln=True)
                pdf.image(chart_path, w=120)
                pdf.ln(3)

            if include_notes and board_notes.strip():
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 8, "Board Notes", ln=True)
                pdf.set_font("Arial", "", 11)
                pdf.multi_cell(0, 8, board_notes)
                pdf.ln(3)

            if include_signature_block:
                pdf.ln(6)
                pdf.cell(0, 8, "_____________________", ln=True)
                pdf.cell(0, 8, "Board Member Signature", ln=True)

            pdf_output = "/tmp/fundsight_board_report.pdf"
            pdf.output(pdf_output)

            msg = MIMEMultipart()
            msg["From"] = st.secrets["email"]["email_user"]
            msg["To"] = recipient_email
            msg["Subject"] = custom_subject
            msg.attach(MIMEText(custom_body, "plain"))

            with open(pdf_output, "rb") as f:
                attachment = MIMEApplication(f.read(), _subtype="pdf")
                attachment.add_header("Content-Disposition", "attachment", filename="fundsight_board_report.pdf")
                msg.attach(attachment)

            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(st.secrets["email"]["email_user"], st.secrets["email"]["email_password"])
                server.send_message(msg)

            st.success("✅ Board Finance Report sent successfully!")

        except Exception as e:
            st.error(f"❌ Error sending PDF: {e}")
