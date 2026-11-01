import re
from app.collectors.gem_document_extractor import GeMDocumentExtractor

def main():
    print("\n======================================")
    print("   GEM ADDRESS EXTRACTION TEST")
    print("======================================")

    # A real GeM tender URL
    tender_no = "GEM/2026/B/7802617"
    link = "https://bidplus.gem.gov.in/showbidDocument/9624352"

    extractor = GeMDocumentExtractor()
    
    # 1. Download and extract the raw text
    print(f"Downloading {tender_no}...")
    document = extractor.download_document(link)
    
    if not document:
        print("Failed to download document.")
        return

    text = extractor.extract_pdf_text(document)
    print(f"Extracted {len(text)} characters of text.\n")

    # 2. Test the current Address Extractor logic
    print("--- CURRENT EXTRACTOR RESULT ---")
    
    address = extractor.extract_address(text)
    if address:
        print(f"FOUND ADDRESS:\n{address}")
    else:
        print("FAILED: extract_address() returned blank.")

    print("\n--- EXTRACTED DISTRICT RESULT ---")
    district = extractor.extract_district(text)
    if district:
        print(f"DISTRICT IDENTIFIED: {district}")
    else:
        print("FAILED: No matching Odisha district found in address.")

if __name__ == "__main__":
    main()