import time
import requests
import hashlib
import json
from bs4 import BeautifulSoup
from typing import List
from datetime import datetime
import urllib3
from urllib.parse import urlparse, urljoin

from app.models.tender import Tender

# Disable SSL warnings (some district govt sites have outdated SSL certificates)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class OdishaDistrictCollector:
    """
    Collector for Odisha District Portals.
    Reads URLs from 'config/websites.json' and scrapes all pages of the standard NIC tender tables.
    """

    MAX_PAGES_PER_DISTRICT = 20  # Safety limit for pagination

    def __init__(self, config_path="config/websites.json"):
        self.config_path = config_path
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        })

    def load_targets_from_config(self) -> List[dict]:
        """Reads the JSON config file to get the target districts and URLs."""
        print(f"Reading target sites from {self.config_path}...")
        targets = []
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                targets = data.get("odisha_districts", [])
        except Exception as e:
            print(f"Failed to read JSON config file: {e}")
            
        print(f"Found {len(targets)} district portals to scan.")
        return targets

    @staticmethod
    def _has_next_page(soup: BeautifulSoup) -> bool:
        """Checks if the page contains a 'Next' pagination link."""
        if soup.find('a', attrs={'rel': 'next'}):
            return True
            
        next_li = soup.find('li', class_=lambda c: c and ('next' in c.lower() or 'pager__item--next' in c.lower()))
        if next_li and next_li.find('a'):
            return True
            
        for a in soup.find_all('a', href=True):
            href_lower = a['href'].lower()
            text_lower = a.text.lower()
            if 'page=' in href_lower and ('next' in text_lower or '›' in a.text or '»' in a.text):
                return True
                
        return False

    def scrape_district(self, district: str, base_url: str) -> List[Tender]:
        all_district_tenders = []
        seen_titles = set()
        page_num = 0

        while page_num < self.MAX_PAGES_PER_DISTRICT:
            # Construct pagination URL (?page=0, ?page=1, ?page=2...)
            if page_num == 0:
                current_url = base_url
            else:
                delimiter = "&" if "?" in base_url else "?"
                current_url = f"{base_url}{delimiter}page={page_num}"

            try:
                response = self.session.get(current_url, timeout=15, verify=False)
                if response.status_code != 200:
                    if page_num > 0:
                        break  # Reached end of available pages
                    print(f"  [ERROR] HTTP {response.status_code} on {district}")
                    return all_district_tenders
                    
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find all tables on the page
                tables = soup.find_all('table')
                if not tables:
                    if page_num == 0:
                        print(f"  [INFO] No active tenders found on {district} table.")
                    break
                
                # --- NEW SMART TABLE SELECTION LOGIC ---
                target_table = None
                title_idx, start_idx, end_idx = -1, -1, -1
                
                for table in tables:
                    first_row = table.find('tr')
                    if not first_row:
                        continue
                        
                    # Check headers in the first row (could be <th> or <td>)
                    headers = [cell.text.strip().lower() for cell in first_row.find_all(['th', 'td'])]
                    
                    for i, header in enumerate(headers):
                        if 'subject' in header or 'title' in header or 'description' in header or 'name of' in header:
                            if title_idx == -1: title_idx = i
                        elif 'start' in header or 'opening' in header or 'publish' in header:
                            start_idx = i
                        elif 'end' in header or 'closing' in header or 'last date' in header:
                            end_idx = i
                            
                    # If we found at least a title column, this is our actual Tender table
                    if title_idx != -1:
                        target_table = table
                        break
                        
                if not target_table:
                    # Fallback to the first table if headers are completely unreadable
                    target_table = tables[0]
                    title_idx, start_idx, end_idx = 1, 4, 5

                rows = target_table.find_all('tr')
                page_tenders = []
                new_titles_on_this_page = 0

                # Skip header row
                for row in rows[1:]:
                    cols = row.find_all('td')
                    
                    if not cols or len(cols) <= title_idx:
                        continue
                        
                    # --- NEW SMART TITLE EXTRACTION ---
                    title = cols[title_idx].text.strip()
                    
                    # ODISHA.GOV.IN TYPO FIX: If 'Subject' is empty, grab the 'Description' column!
                    if not title and len(cols) > title_idx + 1:
                        title = cols[title_idx + 1].text.strip()
                    
                    # Safely extract dates only if those columns exist in the HTML
                    start_date = cols[start_idx].text.strip() if start_idx != -1 and len(cols) > start_idx else ""
                    end_date = cols[end_idx].text.strip() if end_idx != -1 and len(cols) > end_idx else ""
                    
                    if not title or title in seen_titles:
                        continue

                    seen_titles.add(title)
                    new_titles_on_this_page += 1

                    # Find the PDF Download link
                    link = current_url
                    a_tags = row.find_all('a', href=True)
                    pdf_href = None
                    for a in a_tags:
                        href = a['href']
                        if '.pdf' in href.lower() or 'download' in a.text.lower():
                            pdf_href = href
                            break
                    if not pdf_href and a_tags:
                        pdf_href = a_tags[-1]['href']

                    if pdf_href:
                        if pdf_href.startswith('http'):
                            link = pdf_href
                        elif pdf_href.startswith('/'):
                            parsed_uri = urlparse(base_url)
                            base_domain = f"{parsed_uri.scheme}://{parsed_uri.netloc}"
                            link = base_domain + pdf_href
                        else:
                            link = urljoin(base_url, pdf_href)

                    tender_id = f"{district[:3].upper()}-{hashlib.md5(title.encode()).hexdigest()[:6]}"
                    now = datetime.now().isoformat(timespec="seconds")
                    
                    tender = Tender(
                        source="Odisha District Portal",
                        tender_no=tender_id,
                        title=title,
                        department="District Administration",
                        category="General",
                        state="Odisha",
                        district=district,
                        published_date=start_date,
                        closing_date=end_date,
                        link=link,
                        status="Ongoing",
                        first_seen=now,
                        last_seen=now,
                        updated_at=now
                    )
                    page_tenders.append(tender)

                # Reached end of results (empty data rows)
                if new_titles_on_this_page == 0:
                    break

                all_district_tenders.extend(page_tenders)
                print(f"  --> Page {page_num + 1}: Extracted {len(page_tenders)} tenders")

                # Move to next page if pagination exists
                if not self._has_next_page(soup):
                    break

                page_num += 1
                time.sleep(0.5)

            except Exception as e:
                print(f"  [ERROR] Error on {district} Page {page_num + 1}: {e}")
                break

        return all_district_tenders

    def collect(self) -> List[Tender]:
        print("\n======================================")
        print("STARTING ODISHA DISTRICTS EXTRACTION")
        print("======================================")
        
        targets = self.load_targets_from_config()
        all_tenders = []
        
        for target in targets:
            district_name = target.get('name')
            district_url = target.get('url')
            
            if not district_name or not district_url:
                continue

            print(f"Scanning {district_name}...")
            district_tenders = self.scrape_district(district_name, district_url)
            all_tenders.extend(district_tenders)
            print(f"  --> Total for {district_name}: {len(district_tenders)} tenders")
            
        print("\n======================================")
        print(f"Total District Tenders Collected: {len(all_tenders)}")
        print("======================================")
        
        return all_tenders