import json
import os
import re
import tempfile
import time
from typing import Dict, List, Optional

import requests
from pypdf import PdfReader

# Master list of 30 Odisha Districts
ODISHA_DISTRICTS = [
    "Angul", "Balangir", "Balasore", "Bargarh", "Bhadrak", "Boudh",
    "Cuttack", "Deogarh", "Dhenkanal", "Gajapati", "Ganjam", "Jagatsinghpur",
    "Jajpur", "Jharsuguda", "Kalahandi", "Kandhamal", "Kendrapara", "Kendujhar",
    "Khordha", "Koraput", "Malkangiri", "Mayurbhanj", "Nabarangpur", "Nayagarh",
    "Nuapada", "Puri", "Rayagada", "Sambalpur", "Subarnapur", "Sundargarh"
]

# Common spelling variations and aliases in government tender addresses
DISTRICT_ALIASES = {
    "Khordha": ["KHURDA", "BHUBANESWAR"],
    "Kendujhar": ["KEONJHAR"],
    "Subarnapur": ["SONEPUR"],
    "Balangir": ["BOLANGIR"],
    "Balasore": ["BALESHWAR"],
    "Kandhamal": ["PHULBANI"],
}


class GeMDocumentExtractor:
    """
    Stage 2 - GeM Tender Document Extractor
    Downloads a GeM tender document and extracts precise financial and eligibility data.
    Strictly filters out non-English text (e.g., Hindi) before processing.
    """

    MAX_RETRIES = 3
    RETRY_DELAY = 2
    REQUEST_DELAY = 0.5

    DEBUG = True

    def __init__(self, keywords_path: str = "config/keywords.json"):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/pdf,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        self.districts_list = self.load_odisha_districts(keywords_path)

    # ============================================================
    # LOAD DISTRICT KEYWORDS
    # ============================================================

    @staticmethod
    def load_odisha_districts(keywords_file_path: str) -> List[str]:
        """Loads district list from keywords.json or falls back to ODISHA_DISTRICTS."""
        try:
            if os.path.exists(keywords_file_path):
                with open(keywords_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        loaded = data.get("districts") or data.get("odisha_districts")
                        if loaded and isinstance(loaded, list):
                            return loaded
                    elif isinstance(data, list):
                        return data
        except Exception as exc:
            print(f"Could not load {keywords_file_path}: {exc}")
        return ODISHA_DISTRICTS

    # ============================================================
    # DEBUG
    # ============================================================

    @staticmethod
    def debug_print(title: str, value: str) -> None:
        print("\n" + "=" * 70)
        print(title)
        print("=" * 70)
        if value:
            print(value)
        else:
            print("[NOT FOUND]")
        print("=" * 70)

    # ============================================================
    # CLEAN TEXT (ENGLISH & NUMBERS ONLY)
    # ============================================================

    @staticmethod
    def clean_text(text: str) -> str:
        if not text:
            return ""
        
        # Keep only English characters, numbers, and standard punctuation
        text = text.encode("ascii", "ignore").decode("ascii")
        
        text = text.replace("\x00", " ").replace("\r", "\n")
        lines = []
        for line in text.split("\n"):
            line = re.sub(r"[ \t]+", " ", line).strip()
            if line:
                lines.append(line)
        return "\n".join(lines).strip()

    @staticmethod
    def normalize_text(text: str) -> str:
        if not text:
            return ""
        
        text = text.encode("ascii", "ignore").decode("ascii")
        return re.sub(r"\s+", " ", text.replace("\x00", " ")).strip()

    @staticmethod
    def clean_value(value: str) -> str:
        if not value:
            return ""
            
        value = value.encode("ascii", "ignore").decode("ascii")
        value = value.replace("\n", " ")
        value = re.sub(r"\s+", " ", value)
        return value.strip(" :-\t|").strip()

    # ============================================================
    # DOWNLOAD DOCUMENT
    # ============================================================

    def download_document(self, url: str) -> Optional[bytes]:
        if not url:
            return None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                print(f"Downloading document (attempt {attempt}/{self.MAX_RETRIES})")
                response = self.session.get(url, timeout=60, allow_redirects=True)
                print(f"Document HTTP: {response.status_code}")

                if response.status_code == 200:
                    content = response.content
                    if content:
                        if content[:4] == b"%PDF" or b"%PDF" in content[:20] or len(content) > 1000:
                            return content
                print("Unable to download valid document.")
            except requests.RequestException as exc:
                print(f"Document request error: {exc}")

            if attempt < self.MAX_RETRIES:
                time.sleep(self.RETRY_DELAY)
        return None

    # ============================================================
    # EXTRACT PDF TEXT
    # ============================================================

    def extract_pdf_text(self, pdf_bytes: bytes) -> str:
        if not pdf_bytes:
            return ""

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_file.write(pdf_bytes)
                temp_path = temp_file.name

            reader = PdfReader(temp_path)
            print(f"PDF pages: {len(reader.pages)}")

            pages = []
            for page_number, page in enumerate(reader.pages, start=1):
                try:
                    text = page.extract_text()
                    if text:
                        pages.append(f"\n--- PAGE {page_number} ---\n{text}")
                    else:
                        print(f"Page {page_number}: no text")
                except Exception as exc:
                    print(f"Could not extract page {page_number}: {exc}")

            text = "\n".join(pages)
            text = self.clean_text(text)

            if self.DEBUG:
                print(f"Extracted text: {len(text):,} characters")
            return text
        except Exception as exc:
            print(f"PDF extraction failed: {exc}")
            return ""
        finally:
            if temp_path:
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    # ============================================================
    # SEARCH REGEX (PRECISION MATCHING)
    # ============================================================

    @staticmethod
    def first_match(text: str, patterns: List[str]) -> str:
        if not text:
            return ""

        for pattern in patterns:
            try:
                match = re.search(pattern, text, flags=re.IGNORECASE)
                if match:
                    value = match.group(1)
                    if value:
                        return value.strip()
            except Exception:
                continue
        return ""

    def extract_section(self, text: str, headings: List[str], max_chars: int = 200) -> str:
        if not text:
            return ""

        for heading in headings:
            pattern = rf"{heading}(?:\s*[:\-]?\s*)(.{{5,{max_chars}}})"
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                value = match.group(1)
                if value:
                    value = value.split('\n\n')[0] 
                    return self.clean_value(value)
        return ""

    # ============================================================
    # FULL ADDRESS BLOCK EXTRACTION (NEW & HIGHLY FLEXIBLE)
    # ============================================================

    def extract_address(self, text: str) -> str:
        if not text:
            return ""

        # Highly flexible regex to account for hidden PDF slashes, spaces, and newlines
        patterns = [
            r"(Consignees?[\s/]*Reporting[\s/]*Officer.*?)(?=Buyer\s+Added|Buyer\s+Specification|Type\s+of\s+Bid|Time\s+allowed|Bid\s+Document|\Z)",
            r"(Consignees?[\s/]*Detail.*?)(?=Buyer\s+Added|Buyer\s+Specification|Type\s+of\s+Bid|\Z)",
            r"(Delivery[\s/]*Address.*?)(?=Buyer\s+Added|Buyer\s+Specification|Type\s+of\s+Bid|Time\s+allowed|Bid\s+Document|\Z)"
        ]

        for pat in patterns:
            match = re.search(pat, text, flags=re.IGNORECASE | re.DOTALL)
            if match:
                address_block = match.group(1)
                
                # GeM PDFs have huge gaps; allow up to 1500 chars to ensure we grab the actual location
                if len(address_block) > 1500:
                    address_block = address_block[:1500] + "..."
                    
                return self.clean_value(address_block)
        return ""

    # ============================================================
    # DISTRICT (UPGRADED)
    # ============================================================

    def extract_district(self, text: str) -> str:
        if not text:
            return ""

        # 1. Grab the full address block we just created
        address_block = self.extract_address(text)
        search_target = address_block if address_block else text
        cleaned_search_text = re.sub(r"[^\w\s]", " ", search_target).upper()

        # 2. Check canonical district names first
        for district in self.districts_list:
            dist_upper = district.upper()
            pattern = r"\b" + re.escape(dist_upper) + r"\b"
            if re.search(pattern, cleaned_search_text):
                return district.title()

        # 3. Check alias names 
        for canonical, aliases in DISTRICT_ALIASES.items():
            for alias in aliases:
                pattern = r"\b" + re.escape(alias) + r"\b"
                if re.search(pattern, cleaned_search_text):
                    return canonical.title()

        # 4. Fallback to generic regex matching if no master district match was found
        fallback_patterns = [
            r"\b(?:District|Dist)\b\.?\s*[:\-]?\s*([A-Za-z]{3,30})\b",
            r"\b([A-Za-z]{3,30})\s+District\b"
        ]
        
        for pattern in fallback_patterns:
            matches = re.findall(pattern, text, flags=re.IGNORECASE)
            for m in matches:
                cleaned = m.strip().title()
                if cleaned and cleaned.lower() not in ["the", "any", "this", "and", "court", "level", "state"]:
                    return cleaned

        return ""

    # ============================================================
    # QUANTITY
    # ============================================================

    def extract_quantity(self, text: str) -> str:
        patterns = [
            r"Total\s+Quantity\s*[:\-]?\s*([0-9][0-9,]*)",
            r"Total\s+Qty\.?\s*[:\-]?\s*([0-9][0-9,]*)",
            r"Quantity\s*[:\-]?\s*([0-9][0-9,]*)",
            r"(\d+)\s+Total\s+distance\s+in\s+KMs",
            r"\((\d+)\)\s+Technical\s+Specifications"
        ]
        return self.clean_value(self.first_match(text, patterns))

    # ============================================================
    # TENDER VALUE / BUDGET
    # ============================================================

    def extract_tender_value(self, text: str) -> str:
        patterns = [
            r"Estimated\s+Bid\s+Value\s+in\s+INR[^\d]*([\d,]+(?:\.\d+)?)",
            r"Estimated\s+Bid\s+Value\s*(?:\(INR\))?\s*[:\-]?\s*([\d,]{4,}(?:\.\d+)?)",
            r"Tender\s+Value\s*(?:\(INR\))?\s*[:\-]?\s*([\d,]{4,}(?:\.\d+)?)",
            r"Bid\s+Value\s*(?:\(INR\))?\s*[:\-]?\s*([\d,]{4,}(?:\.\d+)?)",
        ]
        return self.clean_value(self.first_match(text, patterns))

    def extract_budget(self, text: str) -> str:
        patterns = [
            r"Budget[^\d]*(?:Rs\.?|INR)?\s*([\d,]+(?:\.\d+)?)",
            r"Estimated\s+Cost[^\d]*(?:Rs\.?|INR)?\s*([\d,]+(?:\.\d+)?)",
            r"Approx(?:imate)?\s+Cost[^\d]*(?:Rs\.?|INR)?\s*([\d,]+(?:\.\d+)?)",
        ]
        return self.clean_value(self.first_match(text, patterns))

    # ============================================================
    # EMD
    # ============================================================

    def extract_emd(self, text: str) -> str:
        patterns = [
            r"EMD\s+Detail\s+Required\s+(Yes|No|[\d,]+)",
            r"EMD\s+Amount\s*(?:\(INR\))?\s*[:\-]?\s*([\d,]{3,}(?:\.\d+)?)",
            r"Earnest\s+Money\s+Deposit\s*(?:\(INR\))?\s*[:\-]?\s*([\d,]{3,}(?:\.\d+)?)",
            r"Bid\s+Security\s*(?:\(INR\))?\s*[:\-]?\s*([\d,]{3,}(?:\.\d+)?)",
        ]
        return self.clean_value(self.first_match(text, patterns))

    # ============================================================
    # EMD ELIGIBILITY / EXEMPTION
    # ============================================================

    def extract_emd_eligibility(self, text: str) -> str:
        patterns = [
            r"EMD\s+Exemption\s*[:\-]?\s*(Yes|No|Allowed|Not Allowed)\b",
            r"Exemption\s+from\s+EMD\s*[:\-]?\s*(Yes|No)\b",
        ]
        return self.clean_value(self.first_match(text, patterns))

    # ============================================================
    # OEM REQUIREMENT
    # ============================================================

    def extract_oem_requirement(self, text: str) -> str:
        patterns = [
            r"OEM\s*[:\-]?\s*(Yes|No)\b",
            r"Manufacturer\s+Authorization\s*[:\-]?\s*(Yes|No)\b",
            r"OEM\s+Authorization\s*[:\-]?\s*(Yes|No)\b",
        ]
        return self.clean_value(self.first_match(text, patterns))

    # ============================================================
    # EXPERIENCE
    # ============================================================

    def extract_past_experience(self, text: str) -> str:
        if "no relevance or bearing" in text.lower() or "not going to be used as a criteria" in text.lower():
            return "Not Required"

        patterns = [
            r"Past\s+Experience\s*[:\-]?\s*(\d+\s*Years?)",
            r"Experience\s+Requirement\s*[:\-]?\s*(\d+\s*Years?)",
            r"Minimum\s+Experience\s*[:\-]?\s*(\d+\s*Years?)",
        ]
        return self.clean_value(self.first_match(text, patterns))

    # ============================================================
    # TURNOVER
    # ============================================================

    def extract_turnover(self, text: str) -> str:
        patterns = [
            r"Average\s+Annual\s+Turnover[^\d]*([\d,]+(?:\.\d+)?\s*(?:Lakhs?|Crores?|Cr\.?|Lacs?|INR)?)",
            r"Minimum\s+Turnover[^\d]*([\d,]+(?:\.\d+)?\s*(?:Lakhs?|Crores?|Cr\.?|Lacs?|INR)?)",
            r"Annual\s+Turnover[^\d]*([\d,]+(?:\.\d+)?\s*(?:Lakhs?|Crores?|Cr\.?|Lacs?|INR)?)",
        ]
        return self.clean_value(self.first_match(text, patterns))

    # ============================================================
    # ADDITIONAL QUALIFICATION
    # ============================================================

    def extract_additional_qualification(self, text: str) -> str:
        headings = [
            r"Additional\s+Qualification\s*/\s*Data\s+Required",
            r"Additional\s+Qualification",
            r"Qualification\s*/\s*Data\s+Required",
        ]
        return self.extract_section(text, headings, max_chars=150)

    # ============================================================
    # DATES & TYPES
    # ============================================================

    def extract_corrigendum(self, text: str) -> str:
        patterns = [r"(Corrigendum\s+No\.?\s*[:\-]?\s*\d+)"]
        return self.clean_value(self.first_match(text, patterns))

    def extract_published_date(self, text: str) -> str:
        date_pattern = r"(\d{1,2}[-/][A-Za-z0-9]+[-/]\d{4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})"
        patterns = [
            rf"Published\s+Date\s*[:\-]?\s*{date_pattern}",
            rf"Bid\s+Start\s+Date\s*[:\-]?\s*{date_pattern}",
        ]
        return self.clean_value(self.first_match(text, patterns))

    def extract_opening_date(self, text: str) -> str:
        date_pattern = r"(\d{1,2}[-/][A-Za-z0-9]+[-/]\d{4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})"
        time_pattern = r"(?:\s*\d{1,2}:\d{2}(?:\s*[AP]M)?)?"
        patterns = [
            rf"Bid\s+Opening\s+Date\s*[:\-]?\s*{date_pattern}{time_pattern}",
            rf"Opening\s+Date\s*[:\-]?\s*{date_pattern}{time_pattern}",
        ]
        return self.clean_value(self.first_match(text, patterns))

    def extract_tender_type(self, text: str) -> str:
        patterns = [
            r"Tender\s+Type\s*[:\-]?\s*([A-Za-z][A-Za-z /_-]{1,50})",
            r"Bid\s+Type\s*[:\-]?\s*([A-Za-z][A-Za-z /_-]{1,50})",
        ]
        return self.clean_value(self.first_match(text, patterns))

    # ============================================================
    # EXTRACT ALL
    # ============================================================

    def extract_all(self, text: str) -> Dict[str, str]:
        return {
            "quantity": self.extract_quantity(text),
            "tender_value": self.extract_tender_value(text),
            "budget": self.extract_budget(text),
            "emd": self.extract_emd(text),
            "emd_eligibility": self.extract_emd_eligibility(text),
            "oem_requirement": self.extract_oem_requirement(text),
            "past_experience": self.extract_past_experience(text),
            "turnover_requirement": self.extract_turnover(text),
            "corrigendum": self.extract_corrigendum(text),
            "published_date": self.extract_published_date(text),
            "opening_date": self.extract_opening_date(text),
            "tender_type": self.extract_tender_type(text),
            "additional_qualification": self.extract_additional_qualification(text),
            "district": self.extract_district(text),
            "address": self.extract_address(text),
            "raw_text": text
        }

    # ============================================================
    # DEBUG EXTRACTED DATA
    # ============================================================

    def print_extracted_data(self, data: Dict[str, str]) -> None:
        print("\nEXTRACTED STAGE 2 FIELDS")
        print("-" * 38)
        for key, value in data.items():
            if key == "raw_text":
                continue
            if value:
                display_value = value if len(value) <= 150 else value[:150] + "..."
                print(f"{key}: {display_value}")
            else:
                print(f"{key}: [NOT FOUND]")

    # ============================================================
    # PROCESS ONE TENDER
    # ============================================================

    def process_tender(self, tender_no: str, link: str, save_text_dump: bool = False) -> Dict[str, str]:
        print("\n" + "=" * 38)
        print(f"STAGE 2: {tender_no}")
        print(f"URL: {link}")
        print("=" * 38)

        if not tender_no or not link:
            return {}

        document = self.download_document(link)
        if not document:
            print("Could not download document.")
            return {}

        print(f"Downloaded: {len(document):,} bytes")
        text = self.extract_pdf_text(document)

        if not text:
            print("No readable PDF text found.")
            return {}

        print(f"Readable text: {len(text):,} characters")
        
        if save_text_dump:
            dump_filename = "output/debug_pdf_text.txt"
            os.makedirs("output", exist_ok=True)
            with open(dump_filename, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"--> Saved raw PDF text to {dump_filename} for debugging!")

        data = self.extract_all(text)
        self.print_extracted_data(data)
        time.sleep(self.REQUEST_DELAY)
        
        return data