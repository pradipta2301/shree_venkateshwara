import re
import time
import requests
from bs4 import BeautifulSoup
import urllib3
from typing import List
from app.models.tender import Tender

# Disable SSL warnings for government websites
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class OCACCollector:
    """
    Collector for Odisha Computer Application Centre (OCAC) Tenders.
    Handles complex card layouts with multiple attached PDFs per tender.
    """
    
    def __init__(self):
        self.url = "https://www.ocac.in/en/tender"
        self.base_url = "https://www.ocac.in"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def collect(self) -> List[Tender]:
        print(f"\nScanning OCAC Tenders: {self.url}")
        tenders_list = []
        
        try:
            response = self.session.get(self.url, verify=False, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all structural containers that hold the text "Tender Document"
            cards = soup.find_all(lambda tag: tag.name in ['div', 'li', 'article'] and 'Tender Document' in tag.get_text() and len(tag.get_text()) < 3000)
            
            # Fallback if standard structure isn't found
            if not cards:
                cards = soup.find_all('div', class_=re.compile(r'card|panel|views-row', re.I))

            for card in cards:
                text_content = card.get_text(separator=' ', strip=True)
                
                # Extract all PDF links and their specific labels (e.g., "RFP Vol-II")
                pdf_details = []
                primary_link = ""
                
                for a_tag in card.find_all('a', href=True):
                    href = a_tag['href']
                    link_text = a_tag.get_text(strip=True)
                    if not link_text:
                        link_text = "Document"
                        
                    if '.pdf' in href.lower():
                        full_link = href if href.startswith('http') else f"{self.base_url}{href}"
                        
                        # Store the formatted label and link
                        pdf_details.append(f"{link_text}: {full_link}")
                        
                        # LOGIC: Ensure Vol-1 or Main RFP is the primary link sent to the AI
                        if not primary_link and ('vol-i' in link_text.lower() or 'vol - i' in link_text.lower() or 'rfp' in link_text.lower()):
                            primary_link = full_link

                if not pdf_details:
                    continue # Skip if no documents are attached
                    
                # If no specific "Vol-I" or "RFP" was found, default to the first PDF
                if not primary_link:
                    # Extract just the URL from the first item in our list
                    primary_link = pdf_details[0].split(": ")[1]

                # Combine all links into a single string for the Excel export
                all_links_str = " | \n".join(pdf_details)

                # Extract Tender Number (e.g., FRA-0029-2026/ENQ/26049)
                tender_no = "OCAC-UNKNOWN"
                no_match = re.search(r'([A-Z0-9]+-[0-9]+-[0-9]+/[A-Z]+/[0-9]+)', text_content)
                if no_match:
                    tender_no = no_match.group(1)
                else:
                    # Fallback: grab the first prominent header element
                    header_tag = card.find(['h2', 'h3', 'h4', 'div'], class_=re.compile(r'header|title', re.I))
                    if header_tag:
                        tender_no = header_tag.get_text(strip=True)[:30]

                # Extract Title
                title_text = text_content.replace(tender_no, "").strip()
                title_clean = re.split(r'Read More|Tender Document', title_text, flags=re.I)[0].strip()
                
                tender = Tender(
                    tender_no=tender_no,
                    title=title_clean,
                    department="OCAC",
                    category="IT / Electronics",
                    state="Odisha",
                    district="Khordha", # OCAC is headquartered in Bhubaneswar
                    link=primary_link,  # AI will read this single link
                    source="OCAC Portal",
                    published_date="",  # <-- FIX APPLIED
                    closing_date=""     # <-- FIX APPLIED
                )
                
                # Store all extracted PDF links in the corrigendum column so they are saved in Excel
                tender.corrigendum = f"All Associated Documents:\n{all_links_str}"

                tenders_list.append(tender)

            print(f"  --> Extracted {len(tenders_list)} tenders from OCAC.")
            
        except Exception as e:
            print(f"  [ERROR] Failed to scrape OCAC: {e}")
            
        return tenders_list