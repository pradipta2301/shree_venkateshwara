import json
import os
from app.collectors.odisha_districts import OdishaDistrictCollector
from app.collectors.district_document_extractor import DistrictDocumentExtractor
from app.filters.keyword_filter import KeywordFilter

def test_district_workflow():
    print("======================================")
    print("  DISTRICT SITES PIPELINE TEST (PRE-AI)")
    print("======================================")

    # 1. Collect tenders from district websites configured in websites.json
    district_collector = OdishaDistrictCollector(config_path="config/websites.json")
    dist_tenders = district_collector.collect()
    print(f"\nCollected {len(dist_tenders)} raw tenders from District Portals.")

    if not dist_tenders:
        print("No district tenders found to test.")
        return

    # 2. Initialize Extractor & Keyword Filter
    district_extractor = DistrictDocumentExtractor()
    keyword_filter = KeywordFilter(config_path="config/keywords.json")

    print("\nStarting Document Download, OCR (1st Page Description), and Content Filtering...\n")

    passed_count = 0
    dropped_count = 0

    # Test up to the first 10 district tenders for quick verification
    for i, tender in enumerate(dist_tenders[:10], 1):
        print(f"[{i}/{len(dist_tenders[:10])}] Testing: {tender.tender_no}")
        print(f"  Title: {tender.title}")
        print(f"  URL: {tender.link}")

        # Download PDF/Web and extract text from the first page (description)
        details = district_extractor.process_tender(tender.tender_no, tender.link, max_pages=1)
        raw_text = details.get("raw_text", "")

        if not raw_text:
            print("  [RESULT] Failed to download document or extract text.")
            dropped_count += 1
            print("-" * 50)
            continue

        # FIX: Temporarily inject PDF text into the title to use the standard .filter() method
        original_title = tender.title
        tender.title = f"{original_title} {raw_text}" 
        
        # Pass the single tender in a list to the existing filter method
        filtered_result = keyword_filter.filter([tender])
        
        # Restore the original title immediately after filtering
        tender.title = original_title

        if filtered_result:
            print("  [PASSED] Tender matched filtration keywords based on document content!")
            passed_count += 1
        else:
            print("  [DROPPED] Document text did not match keywords.")
            dropped_count += 1
            
        print("-" * 50)

    print(f"\nTest Summary: {passed_count} Passed | {dropped_count} Dropped (Pre-AI Step)")

if __name__ == "__main__":
    test_district_workflow()