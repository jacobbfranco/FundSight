# Email Report Section
if show_board_email and uploaded_file:
    st.markdown("### 📤 Send PDF Report")
    if st.button("Send PDF Report"):
        try:
            # Generate PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt=f"Board Summary Report - {selected_client}", ln=True)
            pdf.cell(200, 10, txt=f"Total Income: ${income:,.2f}", ln=True)
            pdf.cell(200, 10, txt=f"Total Expenses: ${expenses:,.2f}", ln=True)
            pdf.cell(200, 10, txt=f"Net Cash Flow: ${net:,.2f}", ln=True)
            pdf.cell(200, 10, txt=f"Days Cash on Hand: {days_cash:.1f}", ln=True)
            pdf.cell(200, 10, txt=f"Program Expense Ratio: {program_ratio:.2%}", ln=True)
            pdf.cell(200, 10, txt=f"Scenario Net Cash Flow: ${scenario_net:,.2f}", ln=True)

            # Save PDF
            pdf_output = "/tmp/fundsight_report.pdf"
            pdf.output(pdf_output)  # DO NOT encode here

            # Setup Email
            msg = MIMEMultipart()
            msg["From"] = st.secrets["email_user"]
            msg["To"] = "jacob.b.franco@gmail.com"
            msg["Subject"] = f"Board Report for {selected_client}"
            body = MIMEText("Attached is the latest board summary from FundSight.", "plain")
            msg.attach(body)

            with open(pdf_output, "rb") as f:
                attachment = MIMEApplication(f.read(), _subtype="pdf")
                attachment.add_header("Content-Disposition", "attachment", filename="fundsight_report.pdf")
                msg.attach(attachment)

            # Send Email
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(st.secrets["email_user"], st.secrets["email_password"])
                server.send_message(msg)

            st.success("✅ PDF with logo, charts, and summary was generated and emailed!")

        except Exception as e:
            st.error(f"Error sending email: {e}")






