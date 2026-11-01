import os
import re
import tempfile
import time
from typing import Dict, Optional

import requests
from bs4 import BeautifulSoup
from pdf2image import convert_from_path
import pytesseract
from playwright.sync_api import sync_playwright


class DistrictDocumentExtractor:
    """
    Stage 2 - District Tender OCR Extractor
    Downloads scanned District PDFs, converts the first few pages to images,
    and runs Optical Character Recognition (OCR) to extract EMD, Cost, and Dates.
    Handles intermediate HTML wrapper pages and dynamic session links from NIC/TendersOdisha portals using Playwright.
    """

    MAX_RETRIES = 3
    RETRY_DELAY = 2

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        
        # Configure Tesseract path
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        
        # Poppler bin path
        self.poppler_path = r"C:\Program Files\poppler-26.02.0\Library\bin"

    def download_document(self, url: str) -> Optional[bytes]:
        """Downloads the PDF from a district or NIC portal URL, using Playwright session fallback for NIC links."""
        if not url or url.lower() == "na":
            return None

        # If it's a TendersOdisha/NIC link, use Playwright to navigate details and click download
        if "tendersodisha.gov.in" in url:
            print("  [NIC Portal] Using Playwright browser to resolve tender document...")
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.goto(url, timeout=45000)
                    page.wait_for_load_state("networkidle")

                    # Look for PDF links or download buttons within the NIC tender details page
                    pdf_link = page.query_selector("a[href*='.pdf'], a[href*='download'], tr td a")
                    
                    if pdf_link:
                        href = pdf_link.get_attribute("href")
                        if href and not href.startswith("http"):
                            href = "https://tendersodisha.gov.in" + href if href.startswith("/") else f"https://tendersodisha.gov.in/nicgep/{href}"
                        
                        print(f"  -> Found document link inside NIC page: {href}")
                        
                        # Trigger download via Playwright's download manager
                        with page.expect_download(timeout=15000) as download_info:
                            pdf_link.click()
                        
                        download = download_info.value
                        path = download.path()
                        if path and os.path.exists(path):
                            with open(path, "rb") as f:
                                pdf_bytes = f.read()
                            browser.close()
                            return pdf_bytes

                    browser.close()
            except Exception as e:
                print(f"  [Error] Playwright NIC document resolution failed: {e}")

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = self.session.get(url, timeout=30, verify=False, allow_redirects=True)
                response.raise_for_status()
                
                content_type = response.headers.get('Content-Type', '')
                
                # Check if the response is an HTML page instead of a direct PDF
                if 'application/pdf' not in content_type.lower() and not url.lower().endswith('.pdf'):
                    if len(response.content) < 150000 and b'html' in response.content.lower()[:500]:
                        print("  [Notice] Intercepted HTML wrapper page. Parsing for true download link...")
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        real_url = None
                        download_tag = soup.find('a', href=lambda x: x and ('download' in x.lower() or 'pdf' in x.lower() or 'servlet' in x.lower() or 'file' in x.lower()))
                        if download_tag:
                            real_url = download_tag.get('href')
                        else:
                            for tag in soup.find_all(['a', 'input', 'area', 'button']):
                                onclick = tag.get('onclick', '')
                                if 'download' in onclick.lower() or 'document' in onclick.lower() or 'popup' in onclick.lower() or 'pdf' in onclick.lower():
                                    match = re.search(r"['\"]([^'\"]+\.pdf[^'\"]*)['\"]", onclick, re.IGNORECASE)
                                    if match:
                                        real_url = match.group(1)
                                        break

                        if real_url:
                            if not real_url.startswith("http"):
                                base_domain = "/".join(url.split("/")[:3])
                                real_url = base_domain + real_url if real_url.startswith("/") else f"{base_domain}/{real_url}"
                            
                            print(f"  -> Resolved real download URL: {real_url}")
                            file_response = self.session.get(real_url, timeout=30, verify=False)
                            file_response.raise_for_status()
                            return file_response.content
                        else:
                            print("  [Error] NIC/District HTML wrapper parsed, but no direct file stream or download script found.")
                            return None

                return response.content
            except requests.exceptions.RequestException as e:
                print(f"Document HTTP Error: {e}")
                time.sleep(self.RETRY_DELAY)
                
        print("Unable to download valid document.")
        return None

    def extract_ocr_text(self, pdf_bytes: bytes, max_pages: int = 10) -> str:
        """Converts the first 'max_pages' of a PDF to images and extracts text."""
        if not pdf_bytes:
            return ""

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_file.write(pdf_bytes)
                temp_path = temp_file.name

            print(f"Converting first {max_pages} pages to images using Poppler...")
            
            images = convert_from_path(
                temp_path, 
                poppler_path=self.poppler_path, 
                last_page=max_pages, 
                fmt="jpeg", 
                dpi=200
            )

            print(f"Running Tesseract OCR on {len(images)} pages...")
            extracted_text = []
            for img in images:
                text = pytesseract.image_to_string(img)
                extracted_text.append(text)

            return "\n--- PAGE BREAK ---\n".join(extracted_text)

        except Exception as e:
            print(f"OCR Extraction Failed: {e}")
            return ""
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass

    def extract_emd(self, text: str) -> str:
        text_lower = text.lower()
        if "emd" not in text_lower and "earnest money" not in text_lower:
            return ""

        patterns = [
            r'emd.*?(?:rs\.?|inr|₹)\s*([\d,]+)',
            r'earnest money.*?(?:rs\.?|inr|₹)\s*([\d,]+)',
            r'(?:rs\.?|inr|₹)\s*([\d,]+).*?emd',
            r'emd(?:.*?)(?:is|of)\s*([\d,]+)',
            r'emd\s*:\s*([\d,]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                val = match.group(1).replace(",", "").strip()
                if val.isdigit() and int(val) > 0:
                    return val
        return ""

    def extract_tender_value(self, text: str) -> str:
        text_lower = text.lower()
        patterns = [
            r'estimated cost.*?(?:rs\.?|inr|₹)\s*([\d,]+)',
            r'tender value.*?(?:rs\.?|inr|₹)\s*([\d,]+)',
            r'approximate cost.*?(?:rs\.?|inr|₹)\s*([\d,]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                val = match.group(1).replace(",", "").strip()
                if val.isdigit() and int(val) > 0:
                    return val
        return ""

    def extract_dates(self, text: str) -> Dict[str, str]:
        dates = {
            "published_date": "",
            "closing_date": ""
        }
        pub_pattern = r'(?:publish|issue|dated).*?(\d{2}[./-]\d{2}[./-]\d{4})'
        pub_match = re.search(pub_pattern, text.lower())
        if pub_match:
            dates["published_date"] = pub_match.group(1).replace(".", "-").replace("/", "-")
            
        close_pattern = r'(?:last date|closing date|submission).*?(\d{2}[./-]\d{2}[./-]\d{4})'
        close_match = re.search(close_pattern, text.lower())
        if close_match:
            dates["closing_date"] = close_match.group(1).replace(".", "-").replace("/", "-")
            
        return dates

    def process_tender(self, tender_no: str, link: str, max_pages: int = 10) -> Dict[str, str]:
        print("\n" + "=" * 38)
        print(f"STAGE 2 (OCR): {tender_no}")
        print(f"URL: {link}")
        
        pdf_bytes = self.download_document(link)
        if not pdf_bytes:
            print("Failed to download PDF.")
            return {}

        text = self.extract_ocr_text(pdf_bytes, max_pages=max_pages)
        if not text:
            print("OCR returned no text.")
            return {}

        print(f"Extracted {len(text):,} characters via OCR.")
        
        dates = self.extract_dates(text)

        data = {
            "emd": self.extract_emd(text),
            "tender_value": self.extract_tender_value(text),
            "published_date": dates["published_date"],
            "closing_date": dates["closing_date"],
            "raw_text": text  
        }

        print("\nOCR EXTRACTION RESULTS:")
        for k, v in data.items():
            if k != "raw_text" and v:
                print(f"{k}: {v}")
                
        return data