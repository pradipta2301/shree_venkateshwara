import re
import requests
from bs4 import BeautifulSoup
from typing import List
from app.models.tender import Tender

class OSICCollector:
    """
    Collector for Odisha Small Industries Corporation Ltd. (OSIC)
    URL: https://www.osicltd.in/Home/Tender
    """
    def __init__(self):
        self.url = "https://www.osicltd.in/Home/Tender"
        self.base_url = "https://www.osicltd.in"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def collect(self) -> List[Tender]:
        print(f"\nScanning OSIC Portal: {self.url}")
        tenders_list = []
        try:
            response = self.session.get(self.url, timeout=30, verify=False)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all download links, then isolate their specific parent container (table/div)
            download_links = soup.find_all('a', href=True)
            seen_links = set()
            
            for a_tag in download_links:
                href = a_tag['href']
                if 'javascript' in href.lower() or '#' in href or href in seen_links:
                    continue
                    
                if 'TenderFile' not in href and not href.lower().endswith('.pdf'):
                    continue
                    
                seen_links.add(href)
                
                link = href if href.startswith('http') else f"{self.base_url}/{href.lstrip('/')}"
                
                # Isolate the text of the specific tender card
                container = a_tag.find_parent('table')
                if not container:
                    container = a_tag.find_parent('div')
                
                row_text = container.get_text(separator=" ", strip=True) if container else a_tag.parent.get_text(separator=" ", strip=True)
                
                # 1. Extract Description / Title
                title = "OSIC Tender Document"
                desc_match = re.search(r'Description\s*:\s*(.*)', row_text, re.IGNORECASE)
                if desc_match:
                    title = desc_match.group(1).strip()
                
                # 2. Extract Dates (Format: Mmm DD YYYY H:MMPM)
                pub_date = ""
                close_date = ""
                date_matches = re.findall(r'[A-Za-z]{3}\s+\d{1,2}\s+\d{4}\s+\d{1,2}:\d{2}[APM]{2}', row_text)
                if date_matches:
                    pub_date = date_matches[0]
                    # The second date in the row is typically 'Sales Close' or 'Last Date'
                    if len(date_matches) > 1:
                        close_date = date_matches[1]
                        
                # 3. Extract Tender No (e.g., 2188/OSIC/RE or 2031)
                tender_no = "OSIC-UNKNOWN"
                tno_match = re.search(r'Tender No[:\s]*([A-Za-z0-9/_-]+)', row_text, re.IGNORECASE)
                if tno_match:
                    tender_no = f"OSIC-{tno_match.group(1).strip()}"
                else:
                    url_ref_match = re.search(r'(?:ref|notice)[_\s-]*no[_\s-]*([0-9a-zA-Z]+)', link, re.IGNORECASE)
                    if url_ref_match:
                        tender_no = f"OSIC-{url_ref_match.group(1).upper()}"
                        
                tender = Tender(
                    tender_no=tender_no,
                    title=title,
                    department="Odisha Small Industries Corporation (OSIC)",
                    category="State Procurement",
                    state="Odisha",
                    district="",
                    link=link,
                    source="OSIC",
                    published_date=pub_date,
                    closing_date=close_date,
                    opening_date=""
                )
                
                tenders_list.append(tender)
                
            print(f"  --> Extracted {len(tenders_list)} structured tenders from OSIC.")
        except Exception as e:
            print(f"  [ERROR] OSIC collection failed: {e}")

        return tenders_list