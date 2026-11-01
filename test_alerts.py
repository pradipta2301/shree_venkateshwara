import os
from dotenv import load_dotenv
load_dotenv()

from app.models.tender import Tender
from app.notifications.email_notifier import send_email_alert
from app.notifications.whatsapp_notifier import send_whatsapp_alert

def test_notifications():
    print("======================================")
    print("     TESTING NOTIFICATION MODULES     ")
    print("======================================")

    # Instantiate Tender without 'summary' in init
    mock_tender = Tender(
        source="TestPortal",
        tender_no="TEST-TENDER-2026-01",
        title="Supply and Installation of Solar Water Pumping Systems in Test District",
        department="Test Energy Department",
        closing_date="30-09-2026",
        link="https://odisha.gov.in",
        district="Khordha",
        emd="50000"
    )
    
    # Set summary dynamically just like the main pipeline does
    mock_tender.summary = "This is a test notification payload to verify email and WhatsApp dispatch functionality."

    test_tenders_list = [mock_tender]

    print("\n1. Testing Email Alert...")
    send_email_alert(test_tenders_list)

    print("\n2. Testing WhatsApp Alert...")
    send_whatsapp_alert(test_tenders_list)

    print("\nTest execution finished. Check your inbox and WhatsApp!")

if __name__ == "__main__":
    test_notifications()