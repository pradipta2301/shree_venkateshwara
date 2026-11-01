import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List
from app.models.tender import Tender


def send_email_alert(new_tenders: List[Tender]):
    if not new_tenders:
        return

    sender_email = os.environ.get("ALERT_EMAIL_USER")
    sender_password = os.environ.get("ALERT_EMAIL_PASS")
    receivers_raw = os.environ.get("ALERT_EMAIL_RECEIVER", sender_email or "")

    receiver_emails = [email.strip() for email in receivers_raw.split(",") if email.strip()]

    if not sender_email or not sender_password or not receiver_emails:
        print("  [Email] Skipping email alert: Credentials not found in .env")
        return

    print(f"\nSending Email Alerts for {len(new_tenders)} new tenders to {len(receiver_emails)} recipient(s)...")

    html_content = """
    <div style="font-family: 'Segoe UI', Arial, sans-serif; color: #0f172a;">
      <h2 style="color: #1e3a8a; margin-bottom: 4px;">🚨 New Relevant Odisha Tenders Found</h2>
      <p style="color: #475569; font-size: 13px; margin-top: 0;">Shree Venkatesh Enterprises • Tender Intelligence Platform</p>
      <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%; border-color: #cbd5e1; font-size: 13px;">
        <tr style="background-color: #1e3a8a; color: white; text-align: left;">
          <th>Source</th>
          <th>Tender No</th>
          <th>Category</th>
          <th>Title & AI Summary</th>
          <th>District</th>
          <th>Value / EMD</th>
          <th>Closing Date</th>
          <th>Document</th>
        </tr>
    """

    for t in new_tenders:
        val_str = f"₹{t.tender_value}" if getattr(t, "tender_value", "") else "Refer Doc"
        emd_str = f"₹{t.emd}" if getattr(t, "emd", "") else "N/A"
        summary_str = getattr(t, "summary", "")
        summary_html = f"<br><span style='color:#475569;font-size:12px;'><b>Summary:</b> {summary_str}</span>" if summary_str else ""

        html_content += f"""
        <tr>
          <td><b>{t.source}</b></td>
          <td style="font-family: monospace;">{t.tender_no}</td>
          <td>{t.category or 'General'}</td>
          <td><b>{t.title}</b><br><span style="color:#64748b;font-size:11px;">{t.department}</span>{summary_html}</td>
          <td>{t.district or 'Odisha'}</td>
          <td><b>Val:</b> {val_str}<br><b>EMD:</b> {emd_str}</td>
          <td style="color:#dc2626;font-weight:bold;">{t.closing_date or 'N/A'}</td>
          <td><a href="{t.link}" style="background:#2563eb;color:white;padding:6px 10px;text-decoration:none;border-radius:5px;display:inline-block;">View Notice</a></td>
        </tr>
        """

    html_content += """
      </table>
    </div>
    """

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)

            for receiver_email in receiver_emails:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = f"🚨 {len(new_tenders)} New Odisha Tender(s) - Shree Venkatesh Enterprises"
                msg["From"] = sender_email
                msg["To"] = receiver_email
                msg.attach(MIMEText(html_content, "html"))

                server.sendmail(sender_email, receiver_email, msg.as_string())
                print(f"  [Email SUCCESS] Sent to {receiver_email}")

    except Exception as e:
        print(f"  [Email ERROR] Failed to send email: {e}")