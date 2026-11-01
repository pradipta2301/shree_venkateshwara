import json
import time
import re
from typing import Any, Dict, List, Optional
from datetime import datetime

import requests

from app.models.tender import Tender


class GeMCollector:
    """
    GeM Tender Collector
    Scope: GeM only, Odisha search, Ongoing bids
    """

    BASE_URL = "https://bidplus.gem.gov.in"
    ALL_BIDS_URL = "https://bidplus.gem.gov.in/all-bids"
    API_URL = "https://bidplus.gem.gov.in/all-bids-data"

    PAGE_SIZE = 10
    MAX_RETRIES = 3
    RETRY_DELAY = 2

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Connection": "keep-alive",
        })
        self.csrf_token: Optional[str] = None
        self.csrf_cookie_name: Optional[str] = None
        self.total_found: Optional[int] = None

    @staticmethod
    def _first_value(value: Any, default: str = "") -> str:
        if value is None:
            return default
        if isinstance(value, list):
            if not value:
                return default
            value = value[0]
            if value is None:
                return default
        return str(value).strip()

    @staticmethod
    def _clean_text(value: Any, default: str = "") -> str:
        text = GeMCollector._first_value(value, default)
        text = text.replace("\r", " ").replace("\n", " ")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def _get_field(bid: Dict[str, Any], field_names: List[str], default: str = "") -> str:
        for field_name in field_names:
            if field_name in bid:
                value = GeMCollector._clean_text(bid.get(field_name), "")
                if value:
                    return value
        return default

    def open_gem(self) -> None:
        print("Opening GeM...")
        try:
            response = self.session.get(self.ALL_BIDS_URL, timeout=30)
        except requests.RequestException as exc:
            raise Exception(f"Unable to connect to GeM: {exc}")

        if response.status_code != 200:
            raise Exception(f"GeM page failed HTTP {response.status_code}")

        csrf_patterns = [
            r'id=["\']chash["\'][^>]*value=["\']([^"\']+)["\']',
            r'name=["\']csrf_bd_gem_nk["\'][^>]*value=["\']([^"\']+)["\']',
            r'csrf_bd_gem_nk["\']?\s*[:=]\s*["\']([^"\']+)["\']',
        ]

        for pattern in csrf_patterns:
            match = re.search(pattern, response.text, flags=re.IGNORECASE)
            if match:
                self.csrf_token = match.group(1).strip()
                self.csrf_cookie_name = "csrf_bd_gem_nk"
                break

        if not self.csrf_token:
            for cookie in self.session.cookies:
                if cookie.name.lower() in ("csrf_bd_gem_nk", "csrf_gem_cookie"):
                    self.csrf_token = cookie.value
                    self.csrf_cookie_name = cookie.name
                    break

        if not self.csrf_token:
            raise Exception("CSRF token not found")

    def build_payload(self, page: int) -> Dict[str, Any]:
        return {
            "page": page,
            "param": {
                "searchBid": "odisha",
                "searchType": "fullText",
            },
            "filter": {
                "bidStatusType": "ongoing_bids",
                "byType": "all",
                "highBidValue": "",
                "byEndDate": {"from": "", "to": ""},
                "sort": "Bid-End-Date-Oldest",
            }
        }

    def api_headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://bidplus.gem.gov.in",
            "Referer": self.ALL_BIDS_URL,
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": self.session.headers.get("User-Agent", ""),
        }

    def fetch_page(self, page: int) -> Optional[Dict[str, Any]]:
        payload = self.build_payload(page)
        post_data = {
            "payload": json.dumps(payload, separators=(",", ":")),
            "csrf_bd_gem_nk": self.csrf_token,
        }
        headers = self.api_headers()

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = self.session.post(self.API_URL, data=post_data, headers=headers, timeout=45)
            except requests.RequestException as exc:
                print(f"Request error page {page}: {exc}")
                time.sleep(self.RETRY_DELAY)
                continue

            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError:
                    return None

            if response.status_code == 403:
                self.session.close()
                self.session = requests.Session()
                self.csrf_token = None
                self.csrf_cookie_name = None
                self.open_gem()
                post_data["csrf_bd_gem_nk"] = self.csrf_token
                time.sleep(self.RETRY_DELAY)
                continue

            time.sleep(self.RETRY_DELAY)
        return None

    def extract_documents(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            response_data = data.get("response", {}).get("response", {})
            if not isinstance(response_data, dict):
                return []

            total_found = response_data.get("numFound")
            if total_found is not None:
                try:
                    self.total_found = int(total_found)
                except ValueError:
                    pass

            docs = response_data.get("docs", [])
            if isinstance(docs, list):
                return docs
        except Exception:
            pass
        return []

    def handle_lifecycle_event(self, tender_number: str, parent_bid_number: str) -> None:
        """
        Handles GeM Reverse Auction (/R/) notices linked to an existing parent bid (/B/)
        instead of adding them as new opportunities to the public feed.
        """
        print(f"  [LIFECYCLE EVENT] Skipping Reverse Auction {tender_number} (Parent Bid: {parent_bid_number or 'N/A'})")

    def create_tender(self, bid: Dict[str, Any]) -> Optional[Tender]:
        # Exact field mappings based on your terminal output
        tender_number = self._get_field(bid, ["b_bid_number"], "")
        if not tender_number:
            return None

        # Skip adding Reverse Auctions (/R/) as a new opportunity to the public feed
        if tender_number.startswith("GEM/") and "/R/" in tender_number:
            parent_bid_number = self._get_field(
                bid,
                ["b_bid_number_parent", "parent_bid_number", "ba_ref_bid_number", "b_ref_bid_number"],
                ""
            )
            self.handle_lifecycle_event(tender_number, parent_bid_number)
            return None

        title = self._get_field(bid, ["bd_category_name", "b_category_name"], "NA")
        department = self._get_field(bid, ["ba_official_details_deptName"], "NA")
        category = self._get_field(bid, ["bd_category_name", "b_category_name"], "")
        closing_date = self._get_field(bid, ["final_end_date_sort"], "")
        published_date = self._get_field(bid, ["final_start_date_sort"], "")
        quantity = self._get_field(bid, ["b_total_quantity"], "")
        bid_type = self._get_field(bid, ["b_bid_type"], "")
        bid_id = self._get_field(bid, ["b_id", "id"], "")

        if bid_id:
            link = f"{self.BASE_URL}/showbidDocument/{bid_id}"
        else:
            link = self.ALL_BIDS_URL

        now = datetime.now().isoformat(timespec="seconds")

        try:
            tender = Tender(
                source="GeM",
                tender_no=tender_number,
                title=title,
                department=department,
                closing_date=closing_date,
                link=link,
                category=category,
                district="",
                state="Odisha",
                quantity=quantity,
                tender_value="",  # Extracted in Stage 2
                budget="",        # Extracted in Stage 2
                emd="",           # Extracted in Stage 2
                emd_eligibility="",
                oem_requirement="",
                past_experience="",
                turnover_requirement="",
                tender_type="",
                bid_type=bid_type,
                published_date=published_date,
                opening_date="",
                corrigendum="",
                buyer_name="",
                status="Ongoing",
                first_seen=now,
                last_seen=now,
                updated_at=now,
            )
        except TypeError as exc:
            print(f"Tender creation failed {tender_number}: {exc}")
            return None

        return tender

    def collect(self) -> List[Tender]:
        self.open_gem()
        all_tenders = []
        seen = set()
        page = 1

        while True:
            print(f"Fetching GeM page {page}...")
            data = self.fetch_page(page)

            if data is None:
                break

            docs = self.extract_documents(data)
            print(f"Found {len(docs)} records on page {page}")

            if not docs:
                break

            for bid in docs:
                tender = self.create_tender(bid)
                if tender is None:
                    continue

                if tender.tender_no in seen:
                    continue

                seen.add(tender.tender_no)
                all_tenders.append(tender)

            if len(docs) < self.PAGE_SIZE:
                break

            page += 1
            time.sleep(0.5)

        print("\n======================================")
        print(f"Total collected: {len(all_tenders)}")
        print("======================================")

        return all_tenders