import json
import os
import time
from app.collectors.odisha_districts import OdishaDistrictCollector
from app.collectors.district_document_extractor import DistrictDocumentExtractor
from app.collectors.ai_document_extractor import AIDocumentExtractor
from app.filters.keyword_filter import KeywordFilter
from app.models.tender import Tender

def test_websites_json_pipeline():
    print("======================================")
    print("  WEBSITES.JSON PIPELINE TEST SCRIPT  ")
    print("======================================")

    # 1. Collect raw tenders exclusively from config/websites.json
    collector = OdishaDistrictCollector(config_path="config/websites.json")
    raw_tenders = collector.collect()
    print(f"\nCollected {len(raw_tenders)} raw tenders from district portals.")

    if not raw_tenders:
        print("[INFO] No raw tenders collected.")
        return

    district_extractor = DistrictDocumentExtractor()
    ai_extractor = AIDocumentExtractor()
    keyword_filter = KeywordFilter("config/keywords.json")

    tested_count = 0
    matched_count = 0

    # 2. Iterate and process through the content-inspection workflow
    for tender in raw_tenders[:10]:  # Capped at first 10 for rapid testing
        print(f"\n--------------------------------------")
        print(f"Testing Tender: {tender.tender_no}")
        print(f"Portal Source: {tender.source}")
        print(f"Link: {tender.link}")

        # Step A: Download PDF and extract text / OCR
        details = district_extractor.process_tender(tender.tender_no, tender.link)
        raw_text = details.get("raw_text", "") if details else ""

        if not raw_text:
            print("  -> [SKIPPED] No readable text or valid PDF found.")
            continue

        # Step B: Keyword filter check using a temporary Tender object with extracted text
        temp_check_tender = Tender(
            source=tender.source,
            tender_no=tender.tender_no,
            title=tender.title + " " + raw_text,
            department=tender.department,
            district=tender.district,
            link=tender.link,
            closing_date=tender.closing_date  # Added required closing_date field
        )
        
        filtered_result = keyword_filter.filter([temp_check_tender])
        if not filtered_result:
            print("  -> [FILTERED OUT] Document content did not match water filtration keywords.")
            continue

        matched_count += 1
        print("  -> [KEYWORD MATCH!] Keywords found inside document text.")

        # Step C: Send matching content to AI Engine for structured metadata & summary
        print(f"  -> Sending {len(raw_text):,} chars to AI Engine...")
        ai_data = ai_extractor.extract_tender_details(raw_text, source=tender.source)
        
        if ai_data:
            print(f"  -> [AI SUCCESS]")
            print(f"     District: {ai_data.get('district')}")
            print(f"     Quantity: {ai_data.get('quantity')}")
            print(f"     Tender Value: {ai_data.get('tender_value')}")
            print(f"     EMD: {ai_data.get('emd')}")
            print(f"     Summary: {str(ai_data.get('summary'))[:120]}...")
        else:
            print("  -> [AI WARNING] Extraction returned empty.")

        tested_count += 1
        time.sleep(1)

    print(f"\n======================================")
    print(f"Test Complete: Inspected {tested_count} documents, Found {matched_count} matches.")

if __name__ == "__main__":
    test_websites_json_pipeline()