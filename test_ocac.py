import os
import io
import urllib3
import PyPDF2
import requests
from dotenv import load_dotenv

from app.collectors.ocac_collector import OCACCollector
from app.collectors.ai_document_extractor import AIDocumentExtractor

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

def main():
    print("==================================================")
    print("      TESTING OCAC SCRAPER & AI EXTRACTION        ")
    print("==================================================")

    # 1. Run the Collector
    ocac_collector = OCACCollector()
    tenders = ocac_collector.collect()

    if not tenders:
        print("No tenders found or scraped from OCAC!")
        return
        
    print(f"\nSuccessfully scraped {len(tenders)} tenders from OCAC.\n")
    
    # 2. Pick the first tender to test
    test_tender = tenders[0]
    print("--- FIRST TENDER DETAILS ---")
    print(f"Tender No:   {test_tender.tender_no}")
    print(f"Title:       {test_tender.title}")
    print(f"Primary PDF: {test_tender.link}")
    print(f"Other Links (Saved to Corrigendum column):\n{test_tender.corrigendum}")
    print("----------------------------\n")
    
    if not test_tender.link:
        print("No primary link found to test.")
        return

    # 3. Download the Primary PDF
    print(f"Downloading primary PDF from: {test_tender.link}")
    try:
        pdf_resp = requests.get(test_tender.link, verify=False, timeout=30)
        pdf_resp.raise_for_status()
        pdf_bytes = pdf_resp.content
        print(f"Downloaded {len(pdf_bytes):,} bytes.")
    except Exception as e:
        print(f"Failed to download PDF: {e}")
        return

    # 4. Extract Text using PyPDF2 (Digital Extraction)
    print("Extracting text digitally (first 15 pages)...")
    raw_text = ""
    try:
        pdf_file = io.BytesIO(pdf_bytes)
        reader = PyPDF2.PdfReader(pdf_file)
        # Just grab the first 15 pages for speed 
        for i in range(min(15, len(reader.pages))):
            page_text = reader.pages[i].extract_text()
            if page_text:
                raw_text += page_text + "\n"
        print(f"Extracted {len(raw_text):,} characters of text.")
    except Exception as e:
        print(f"Failed to extract text from PDF: {e}")
        return

    if not raw_text.strip():
        print("No text could be extracted. Document might be purely scanned images.")
        return

    # 5. Run AI Analysis
    print("\nSending text to AI Engine for deep analysis...")
    ai_extractor = AIDocumentExtractor()
    ai_data = ai_extractor.extract_tender_details(raw_text, source="OCAC Portal")
    
    print("\n--- AI STRUCTURED OUTPUT (OCAC) ---")
    if ai_data:
        for k, v in ai_data.items():
            if v:
                print(f"  {k:20}: {v}")
    else:
        print("  [AI ERROR] Empty result returned.")

if __name__ == "__main__":
    main()