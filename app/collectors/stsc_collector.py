import requests
from bs4 import BeautifulSoup
from typing import List
from app.models.tender import Tender

class STSCCollector:
    """
    Collector for ST & SC Development, Minorities & Backward Classes Welfare Department
    URL: https://stsc.odisha.gov.in/en/tenders-advertisement
    """
    def __init__(self):
        self.url = "https://stsc.odisha.gov.in/en/tenders-advertisement"
        self.base_url = "https://stsc.odisha.gov.in"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def collect(self) -> List[Tender]:
        print(f"\nScanning STSC Portal: {self.url}")
        tenders_list = []
        
        try:
            response = self.session.get(self.url, timeout=30, verify=False)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Locate the main data tables
            tables = soup.find_all('table')
            if not tables:
                print("  [ERROR] No tables found on STSC page.")
                return tenders_list
                
            # Iterate through rows of the primary table
            target_table = tables[0]
            rows = target_table.find_all('tr')
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                
                # Skip header rows or malformed rows (Requires at least 6 columns based on the UI)
                if not cells or cells[0].name == 'th' or len(cells) < 6:
                    continue
                    
                # Map data strictly to the visual columns: 
                # [0: Sl. No., 1: Title, 2: Start Date, 3: End Date, 4: Tender Number, 5: Download]
                title = cells[1].get_text(strip=True)
                start_date = cells[2].get_text(strip=True)
                end_date = cells[3].get_text(strip=True)
                tender_no = cells[4].get_text(strip=True)
                
                if not tender_no or tender_no.lower() in ['na', '-', '']:
                    tender_no = "STSC-UNKNOWN"
                    
                # Locate the PDF link inside the Details/Download column
                download_cell = cells[5]
                a_tag = download_cell.find('a', href=True)
                
                if not a_tag:
                    continue
                    
                href = a_tag['href']
                
                # Construct the absolute direct file link
                if href.startswith('http'):
                    link = href
                else:
                    link = f"{self.base_url}/{href.lstrip('/')}"
                    
                tender = Tender(
                    tender_no=tender_no,
                    title=title,
                    department="ST & SC Development, Minorities & Backward Classes Welfare Department",
                    category="State Procurement",
                    state="Odisha",
                    district="",
                    link=link,
                    source="STSC",
                    published_date=start_date,
                    closing_date=end_date,
                    opening_date=""
                )
                tenders_list.append(tender)
                
            print(f"  --> Extracted {len(tenders_list)} structured tenders from STSC.")
            
        except Exception as e:
            print(f"  [ERROR] STSC collection failed: {e}")

        return tenders_list