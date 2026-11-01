import re
from typing import List
from playwright.sync_api import sync_playwright
from app.models.tender import Tender

class OdishaPortalCollector:
    """
    Collector for official Government of Odisha portal listings:
    - odisha.gov.in/en/all-tenders
    - odisha.gov.in/en/all-tenders-quotation
    Parses explicit table cells for Title, Start Date, End Date, Tender No, 
    Department, and captures all attached documents.
    """
    def __init__(self):
        self.base_urls = [
            "https://odisha.gov.in/en/all-tenders",
            "https://odisha.gov.in/en/all-tenders-quotation"
        ]
        self.base_url = "https://odisha.gov.in"

    def collect(self) -> List[Tender]:
        print("\nScanning Official Odisha Govt Portal Tenders & Quotations (Structured Table)...")
        tenders_list = []
        seen_links = set()

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                
                for base_url in self.base_urls:
                    page_num = 0
                    max_pages = 5
                    
                    while page_num < max_pages:
                        target_url = f"{base_url}?page={page_num}" if page_num > 0 else base_url
                        print(f"  -> Fetching: {target_url}")
                        
                        try:
                            page.goto(target_url, timeout=60000)
                            page.wait_for_selector("table", timeout=10000)
                            
                            rows_data = page.evaluate("""() => {
                                const results = [];
                                const rows = document.querySelectorAll('tr');
                                rows.forEach(row => {
                                    const cells = row.querySelectorAll('td');
                                    if (cells.length >= 6) {
                                        const links = Array.from(row.querySelectorAll('a')).map(a => ({
                                            href: a.getAttribute('href') || '',
                                            text: a.innerText.trim()
                                        })).filter(l => l.href);

                                        results.push({
                                            title: cells[1] ? cells[1].innerText.trim() : '',
                                            start_date: cells[2] ? cells[2].innerText.trim() : '',
                                            end_date: cells[3] ? cells[3].innerText.trim() : '',
                                            tender_no: cells[4] ? cells[4].innerText.trim() : '',
                                            department: cells[5] ? cells[5].innerText.trim() : '',
                                            links: links
                                        });
                                    }
                                });
                                return results;
                            }""")

                            if not rows_data:
                                break

                            page_new_items = 0
                            for item in rows_data:
                                raw_title = item['title']
                                if not raw_title or len(raw_title) < 5 or "Title" in raw_title:
                                    continue

                                tender_no = item['tender_no'] if item['tender_no'] else "ODISHA-GOV-UNKNOWN"
                                start_date = item['start_date']
                                end_date = item['end_date']
                                department = item['department'] if item['department'] else "Odisha Government Portal"
                                
                                # Clean title without stripping valid prefix numbers that are part of tender references
                                clean_title = raw_title.replace('NEW', '').strip()

                                for link_obj in item['links']:
                                    href = link_obj['href']
                                    if 'pdf' not in href.lower() and 'download' not in href.lower() and 'file' not in href.lower():
                                        continue

                                    link = href if href.startswith("http") else f"{self.base_url}{href if href.startswith('/') else '/' + href}"

                                    if link in seen_links:
                                        continue
                                    seen_links.add(link)
                                    page_new_items += 1

                                    tender = Tender(
                                        tender_no=tender_no,
                                        title=clean_title,
                                        department=department,
                                        category="State Procurement / Quotation",
                                        state="Odisha",
                                        district="",
                                        link=link,
                                        source="OdishaGovPortal",
                                        published_date=start_date,
                                        closing_date=end_date,
                                        opening_date=""
                                    )
                                    tenders_list.append(tender)

                            if page_new_items == 0:
                                break

                            page_num += 1

                        except Exception as sub_e:
                            print(f"  [INFO] Reached end or timeout on pagination for {base_url} at page {page_num}")
                            break

                browser.close()
            print(f"  --> Extracted {len(tenders_list)} structured records including additional documents from Odisha portal.")
        except Exception as e:
            print(f"  [ERROR] Playwright collection failed for Odisha Portal: {e}")

        return tenders_list