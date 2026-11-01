import os
from typing import List
from app.models.tender import Tender


def send_whatsapp_alert(new_tenders: List[Tender]):
    if not new_tenders:
        return

    phones_raw = os.environ.get("WHATSAPP_ALERT_NUMBER", "")
    phone_numbers = [num.strip() for num in phones_raw.split(",") if num.strip()]

    if not phone_numbers:
        print("  [WhatsApp] Skipping WhatsApp alert: WHATSAPP_ALERT_NUMBER not found in .env")
        return

    # Lazy import pywhatkit inside the function to prevent startup/connection crashes on import
    try:
        import pywhatkit as kit
    except Exception as e:
        print(f"  [WhatsApp ERROR] Could not load pywhatkit module: {e}")
        return

    print(f"\nPreparing WhatsApp Alerts for {len(new_tenders)} new tenders to {len(phone_numbers)} number(s)...")
    
    message = f"🚨 *{len(new_tenders)} New Tenders Found!* 🚨\n\n"
    for i, t in enumerate(new_tenders[:5], 1):
        message += f"{i}. *{t.tender_no}*\n{t.title[:60]}...\n📍 District: {t.district or 'N/A'}\n⏳ Close: {t.closing_date}\n🔗 {t.link}\n\n"
    
    if len(new_tenders) > 5:
        message += f"_...and {len(new_tenders) - 5} more inside your Excel report._"

    for phone_number in phone_numbers:
        try:
            print(f"  -> Dispatching WhatsApp message to {phone_number}...")
            kit.sendwhatmsg_instantly(phone_number, message, wait_time=15, tab_close=True)
            print(f"  [WhatsApp SUCCESS] Message sent to {phone_number}!")
        except Exception as e:
            print(f"  [WhatsApp ERROR] Failed to send message to {phone_number}: {e}")