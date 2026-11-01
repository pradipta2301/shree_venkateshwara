import re
from typing import Dict

class LocalDocumentExtractor:
    """
    Lightning-fast, 100% free local regex extractor. 
    Parses PDF/OCR text for EMD, tender value, and dates instantly.
    """

    def extract_tender_details(self, raw_text: str, source: str = "District") -> Dict[str, str]:
        if not raw_text:
            return {}

        text_lower = raw_text.lower()

        # 1. EMD Extraction
        emd = ""
        emd_match = re.search(r"(?:emd|earnest\s+money).*?rs\.?\s*([\d,]+)", text_lower)
        if emd_match:
            emd = emd_match.group(1).strip()
        elif "exempted" in text_lower or "exemption" in text_lower:
            emd = "Exempted"

        # 2. Tender Value Extraction
        tender_value = ""
        val_match = re.search(r"(?:estimated\s+cost|approx\s+value|tender\s+value).*?rs\.?\s*([\d,]+)", text_lower)
        if val_match:
            tender_value = val_match.group(1).strip()

        # 3. Dates Extraction (DD-MM-YYYY format)
        dates = re.findall(r"(\d{2}[-./]\d{2}[-./]202\d)", raw_text)
        published_date = dates[0] if dates else ""
        closing_date = dates[-1] if len(dates) > 1 else ""

        # 4. Address Extraction (Look for typical address markers)
        address = ""
        addr_keywords = ["address", "office of", "consignee", "delivery location"]
        for kw in addr_keywords:
            pos = text_lower.find(kw)
            if pos != -1:
                address = raw_text[pos:pos+150].replace("\n", " ").strip()
                break

        return {
            "district": "",
            "address": address,
            "quantity": "",
            "tender_value": tender_value,
            "budget": "",
            "emd": emd,
            "emd_eligibility": "",
            "oem_requirement": "",
            "past_experience": "",
            "turnover_requirement": "",
            "tender_type": "Open Tender" if "open" in text_lower else "Limited",
            "published_date": published_date,
            "opening_date": "",
            "closing_date": closing_date,
            "corrigendum": ""
        }