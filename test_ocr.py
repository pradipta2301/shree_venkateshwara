from app.collectors.district_document_extractor import DistrictDocumentExtractor

def main():
    print("======================================")
    print("   DISTRICT OCR ENGINE TEST")
    print("======================================")

    # Let's use the exact Mayurbhanj LLIN Mosquito Net PDF we found earlier!
    tender_no = "MAY-LLIN-TEST"
    link = "https://mayurbhanj.odisha.gov.in/sites/default/files/2026-07/3606%20dt%2027.07.2026.pdf"

    extractor = DistrictDocumentExtractor()
    
    print("Starting Extraction...")
    results = extractor.process_tender(tender_no, link)
    
    print("\n======================================")
    print("RAW OCR TEXT SNIPPET (First 500 chars):")
    print("======================================")
    print(results.get("raw_ocr_text", "No text found"))

if __name__ == "__main__":
    main()