import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List
import re
from app.collectors.base_collector import BaseCollector
from app.models.tender import Tender

class UrbanTransportCollector(BaseCollector):
    def __init__(self):
        super().__init__()
        self.portals = [
            {
                "name": "Bhubaneswar Smart City",
                "active_url": "https://smartcitybhubaneswar.gov.in/tender",
                "archive_url": "https://smartcitybhubaneswar.gov.in/archiveTender",
                "base_domain": "https://smartcitybhubaneswar.gov.in"
            },
            {
                "name": "Capital Region Transport (CRUT)",
                "active_url": "https://www.comprehensiveregiontransport.in/tenders",
                "archive_url": "https://www.comprehensiveregiontransport.in/archiveTender",
                "base_domain": "https://www.comprehensiveregiontransport.in"
            },
            {
                "name": "Bhubaneswar Development Authority (BDA)",
                "active_url": "https://bda.gov.in/tender/tenders",
                "archive_url": "https://bda.gov.in/archiveTender",
                "base_domain": "https://bda.gov.in"
            }
        ]

    def collect(self) -> List[Tender]:
        tenders = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        for portal in self.portals:
            for url_type, url in [("Active", portal["active_url"]), ("Archive", portal["archive_url"])]:
                try:
                    response = requests.get(url, headers=headers, timeout=15)
                    if response.status_code != 200:
                        continue
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    panels = soup.find_all('div', class_='tenderpanel')
                    
                    for panel in panels:
                        # 1. Extract Tender No
                        t_no_tag = panel.find('p', class_='tenderno')
                        tender_no = t_no_tag.find('span').get_text(strip=True) if t_no_tag and t_no_tag.find('span') else "UNKNOWN"
                        
                        # 2. Extract Title
                        title_tag = panel.find('h4')
                        title = title_tag.get_text(strip=True) if title_tag else "Untitled Tender"
                        
                        # 3. Extract Closing Date
                        closing_date = None
                        date_tags = panel.find_all('p', class_='tenderdate')
                        for tag in date_tags:
                            text = tag.get_text()
                            if 'Closing' in text or 'Closing On' in text:
                                match = re.search(r'(\d{2}-\d{2}-\d{4})', text)
                                if match:
                                    try:
                                        closing_date = datetime.strptime(match.group(1), '%d-%m-%Y')
                                    except ValueError:
                                        pass

                        # 4. Extract PDF Links (handles multiple documents per panel like NIT, RFP, Corrigendum)
                        pdf_tags = panel.find_all('a', class_='pdf')
                        for pdf_tag in pdf_tags:
                            link = pdf_tag.get('href', '')
                            if link and not link.startswith('http'):
                                link = portal["base_domain"] + link if link.startswith('/') else portal["base_domain"] + '/' + link
                            
                            if link:
                                # Identify document type label if available (e.g. NIT, RFP)
                                download_div = pdf_tag.find_parent('div', class_='downloadlist')
                                doc_type = ""
                                if download_div:
                                    div_text = download_div.get_text(strip=True)
                                    doc_type = div_text.replace(pdf_tag.get_text(strip=True), "").strip()
                                    if not doc_type:
                                        doc_type = "DOC"
                                
                                unique_tender_no = f"{tender_no} [{doc_type}]" if doc_type and len(pdf_tags) > 1 else tender_no

                                tender_obj = Tender(
                                    tender_no=unique_tender_no,
                                    title=title,
                                    department=portal["name"],
                                    source="Urban Transport",
                                    link=link,
                                    published_date=datetime.now(),
                                    closing_date=closing_date
                                )
                                
                                if not any(t.link == link for t in tenders):
                                    tenders.append(tender_obj)

                except Exception as e:
                    print(f"Error scraping {portal['name']} ({url_type}): {e}")
                    
        return tenders