import re
from typing import List, Dict
from playwright.sync_api import sync_playwright
from app.models.tender import Tender

class TendersOdishaCollector:
    """
    Collector for official TendersOdisha (GePNIC).
    Collects active tenders by organisation, and extracts complete metadata 
    directly from the Tender Details HTML page to bypass PDF download captchas.
    """
    def __init__(self):
        self.org_url = "https://tendersodisha.gov.in/nicgep/app?page=FrontEndTendersByOrganisation&service=page"
        self.base_url = "https://tendersodisha.gov.in"

    def _normalize_link(self, href: str) -> str:
        if not href:
            return ""
        if href.startswith("http"):
            return href
        if href.startswith("/"):
            return f"{self.base_url}{href}"
        if href.startswith("app"):
            return f"{self.base_url}/nicgep/{href}"
        if href.startswith("?"):
            return f"{self.base_url}/nicgep/app{href}"
        return f"{self.base_url}/nicgep/{href}"

    def collect(self) -> List[Tender]:
        print(f"\nScanning Official NIC Portal (By Organisation) via Playwright: {self.org_url}")
        tenders_list = []

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                
                # STEP 1: Load 'Tenders by Organisation' page
                page.goto(self.org_url, timeout=60000)
                page.wait_for_selector("table", timeout=15000)
                
                org_links = page.evaluate("""() => {
                    const links = [];
                    document.querySelectorAll('tr').forEach(row => {
                        if (row.querySelector('table')) return;
                        const cells = row.querySelectorAll('td');
                        if (cells.length >= 3) {
                            const aTag = cells[cells.length - 1].querySelector('a');
                            if (aTag && !isNaN(parseInt(aTag.innerText.trim()))) {
                                const href = aTag.getAttribute('href');
                                if (href && !href.includes('gepnicreports') && !href.includes('MIS')) {
                                    links.push(href);
                                }
                            }
                        }
                    });
                    return links;
                }""")
                
                print(f"  --> Found {len(org_links)} organizations with active tenders. Scanning lists...")
                seen_tender_links = set()

                # STEP 2: Loop through organizations
                for index, org_href in enumerate(org_links):
                    try:
                        list_url = self._normalize_link(org_href)
                        page.goto(list_url, timeout=45000)
                        page.wait_for_timeout(2000)
                        
                        tenders_data = page.evaluate("""() => {
                            const results = [];
                            document.querySelectorAll('tr').forEach(row => {
                                if (row.querySelector('table')) return;
                                const cells = row.querySelectorAll('td');
                                if (cells.length < 6) return;

                                const aTag = row.querySelector('a[href*="FrontEndViewTender"]');
                                if (!aTag) return;

                                const pubDateText = cells[1].innerText.trim();
                                if (!/\\d{2}-[A-Za-z]{3}-\\d{4}/.test(pubDateText)) return;

                                results.push({
                                    published_date: pubDateText,
                                    closing_date: cells[2].innerText.trim(),
                                    opening_date: cells[3].innerText.trim(),
                                    full_text: cells[4].innerText.trim(),
                                    org_chain: cells[5].innerText.trim(),
                                    href: aTag.getAttribute('href')
                                });
                            });
                            return results;
                        }""")

                        for item in tenders_data:
                            href = item['href']
                            if not href or href in seen_tender_links:
                                continue
                            seen_tender_links.add(href)

                            details_link = self._normalize_link(href)
                            full_text = item['full_text']

                            brackets = re.findall(r'\[(.*?)\]', full_text, flags=re.DOTALL)
                            title = ""
                            tender_no = "NIC-UNKNOWN"

                            if len(brackets) >= 2:
                                title = brackets[0].strip()
                                tender_no = brackets[1].strip()
                            elif len(brackets) == 1:
                                title = brackets[0].strip()
                            else:
                                title = full_text.split("\n")[0].strip()

                            if tender_no == "NIC-UNKNOWN":
                                id_match = re.search(r'\d{4}_[A-Z0-9]+_\d+_\d+', full_text)
                                if id_match:
                                    tender_no = id_match.group(0)

                            title = re.sub(r'\s+', ' ', title).strip()
                            tender_no = re.sub(r'\s+', ' ', tender_no).strip()

                            tender = Tender(
                                tender_no=tender_no,
                                title=title,
                                department=item['org_chain'],
                                category="State Procurement",
                                state="Odisha",
                                district="",
                                link=details_link,
                                source="TendersOdisha",
                                published_date=item['published_date'],
                                closing_date=item['closing_date'],
                                opening_date=item['opening_date']
                            )
                            tenders_list.append(tender)
                            
                    except Exception as e:
                        print(f"  [Warning] Failed to scan organization at index {index}: {e}")
                        continue

                browser.close()
            print(f"  --> Extracted {len(tenders_list)} clean live tenders from TendersOdisha.")
        except Exception as e:
            print(f"  [ERROR] Playwright collection failed for TendersOdisha: {e}")

        return tenders_list

    def extract_details(self, url: str) -> Dict[str, str]:
        """
        Loads the Tender Details page directly to scrape EMD, Value, Fee, and Type.
        Avoids clicking any document link to bypass CAPTCHA.
        """
        result = {
            "tender_value": "",
            "emd": "",
            "emd_eligibility": "",
            "tender_type": "",
            "tender_fee": "",
            "category": "",
            "summary": "",
            "page_url": url
        }

        if not url or not url.startswith("http"):
            return result

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page.goto(url, timeout=45000)
                page.wait_for_selector("table", timeout=15000)
                
                result["page_url"] = page.url

                # Scrape all key-value cells across all tables on the details view
                field_map = page.evaluate("""() => {
                    const data = {};
                    document.querySelectorAll('tr').forEach(row => {
                        const cells = Array.from(row.querySelectorAll('td, th')).map(c => c.innerText.trim());
                        if (cells.length === 2) {
                            if (cells[0] && cells[1]) data[cells[0]] = cells[1];
                        } else if (cells.length >= 4) {
                            for (let i = 0; i < cells.length - 1; i += 2) {
                                if (cells[i] && cells[i+1]) data[cells[i]] = cells[i+1];
                            }
                        }
                    });
                    return data;
                }""")

                for key, val in field_map.items():
                    k_lower = key.lower()

                    if "emd amount" in k_lower:
                        num_match = re.search(r'[\d,]+', val)
                        if num_match and num_match.group(0).replace(',', '').isdigit():
                            result["emd"] = num_match.group(0)

                    elif "emd exemption" in k_lower:
                        result["emd_eligibility"] = val

                    elif "tender value" in k_lower or "estimated cost" in k_lower:
                        num_match = re.search(r'[\d,]+', val)
                        if num_match and num_match.group(0).replace(',', '').isdigit() and int(num_match.group(0).replace(',', '')) > 0:
                            result["tender_value"] = num_match.group(0)

                    elif k_lower == "tender type":
                        result["tender_type"] = val

                    elif k_lower == "tender category":
                        result["category"] = val

                    elif "tender fee in" in k_lower or k_lower == "tender fee":
                        num_match = re.search(r'[\d,]+', val)
                        if num_match:
                            result["tender_fee"] = num_match.group(0)

                # Compose summary
                summary_parts = []
                if result.get("category"): summary_parts.append(f"Category: {result['category']}")
                if result.get("tender_type"): summary_parts.append(f"Type: {result['tender_type']}")
                if result.get("tender_value"): summary_parts.append(f"Value: ₹{result['tender_value']}")
                if result.get("emd"): 
                    exemp = f" (Exemption: {result['emd_eligibility']})" if result.get("emd_eligibility") else ""
                    summary_parts.append(f"EMD: ₹{result['emd']}{exemp}")
                if result.get("tender_fee"): summary_parts.append(f"Fee: ₹{result['tender_fee']}")
                
                result["summary"] = " | ".join(summary_parts) if summary_parts else "Details captured directly from NIC portal."
                browser.close()
        except Exception as e:
            print(f"  [Error] Failed to extract NIC details from page: {e}")

        return result