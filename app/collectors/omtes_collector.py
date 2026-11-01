import re
from typing import List
from playwright.sync_api import sync_playwright
from app.models.tender import Tender

class OMTESCollector:
    """
    Collector for Odisha Model Tribal Education Society (OMTES) tenders
    using Playwright to scrape rendered tender cards and download links,
    including full pagination support.
    """
    def __init__(self):
        self.url = "https://omtes.odisha.gov.in/#/tender"
        self.base_url = "https://omtes.odisha.gov.in"

    def collect(self) -> List[Tender]:
        print(f"\nScanning OMTES Portal via Playwright: {self.url}")
        tenders_list = []

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                
                page.goto(self.url, timeout=60000)
                # Wait for initial tender cards to render
                page.wait_for_timeout(4000)

                seen_titles = set()
                
                while True:
                    # Extract structured card data from the current page DOM
                    cards_data = page.evaluate("""() => {
                        const results = [];
                        const cards = document.querySelectorAll('div, article');
                        cards.forEach(card => {
                            const text = card.innerText;
                            if (text && text.includes('Closing:') && (text.includes('Tender') || text.includes('Notice'))) {
                                const titleElem = card.querySelector('h2, h3, h4, p, strong');
                                const aTag = card.querySelector('a');
                                
                                results.push({
                                    text: text.trim(),
                                    title: titleElem ? titleElem.innerText.trim() : text.substring(0, 100),
                                    href: aTag ? aTag.getAttribute('href') : ''
                                });
                            }
                        });
                        return results;
                    }""")

                    # Process extracted cards for this page
                    for item in cards_data:
                        card_text = item['text']
                        title = item['title']
                        href = item['href']

                        if not title or title in seen_titles or len(title) < 10:
                            continue
                        seen_titles.add(title)

                        # Extract Ref No
                        tender_no = "OMTES-UNKNOWN"
                        ref_match = re.search(r'Ref\s*No[:\s]+([^\n]+)', card_text, re.IGNORECASE)
                        if ref_match:
                            tender_no = ref_match.group(1).strip()

                        # Extract Closing Date
                        closing_date = ""
                        close_match = re.search(r'Closing:\s*([0-9]{2}\s+[A-Za-z]+\s+[0-9]{4})', card_text)
                        if close_match:
                            closing_date = close_match.group(1).strip()

                        # Normalize download link
                        link = self.base_url
                        if href:
                            link = href if href.startswith("http") else f"{self.base_url}/{href.lstrip('/')}"

                        tender = Tender(
                            tender_no=tender_no,
                            title=title,
                            department="Odisha Model Tribal Education Society (OMTES)",
                            category="State Procurement",
                            state="Odisha",
                            district="",
                            link=link,
                            source="OMTES",
                            published_date="",
                            closing_date=closing_date,
                            opening_date=""
                        )
                        tenders_list.append(tender)

                    # Pagination: Attempt to find and click the "Next" button
                    try:
                        # Looks for a standard pagination 'Next' or '>' button
                        next_button = page.locator("button, a").filter(has_text=re.compile(r"^(Next|>|»)$", re.IGNORECASE)).first
                        
                        if next_button.is_visible() and next_button.is_enabled():
                            print("  [OMTES] Navigating to next page...")
                            next_button.click()
                            page.wait_for_timeout(3000) # Wait for new cards to render over network
                        else:
                            break # No active 'Next' button found, exit pagination loop
                    except Exception:
                        break # Failed to interact with pagination, exit loop

                browser.close()
            print(f"  --> Extracted {len(tenders_list)} structured tenders from OMTES via Playwright.")
        except Exception as e:
            print(f"  [ERROR] OMTES Playwright collection failed: {e}")

        return tenders_list