import json
import requests
from app.collectors.gem import GeMCollector
from app.filters.keyword_filter import KeywordFilter

def test_gem_collection():
    print("==================================================")
    print("       ISOLATED GeM TENDER COLLECTION TEST        ")
    print("==================================================")

    target_bid = "GEM/2026/B/7902158"
    
    # 1. Initialize GeM Collector
    collector = GeMCollector()
    print("[1] Fetching live tenders from GeM API...")
    gem_tenders = collector.collect()
    print(f"Total GeM tenders fetched in this run: {len(gem_tenders)}")

    # 2. Check if the specific target bid is in the raw fetched list
    found_raw = None
    for t in gem_tenders:
        if t.tender_no.strip().upper() == target_bid.upper():
            found_raw = t
            break

    if found_raw:
        print(f"\n[SUCCESS] Target bid {target_bid} FOUND in raw GeM collection!")
        print(f"  - Title       : {found_raw.title}")
        print(f"  - Department  : {found_raw.department}")
        print(f"  - State       : {found_raw.state}")
        print(f"  - District    : {found_raw.district}")
    else:
        print(f"\n[MISSING] Target bid {target_bid} was NOT found in the raw GeM fetch.")
        print("Reason: The GeM public portal pagination or state filter skipped it, or it hasn't indexed into the current API payload response window.")

    # 3. Test Keyword Filter specifically on this bid if found, or show keywords
    print("\n[2] Testing Keyword Filter Evaluation...")
    keyword_filter = KeywordFilter("config/keywords.json")
    
    if found_raw:
        filtered_list = keyword_filter.filter([found_raw])
        if filtered_list:
            print(f"[PASSED] Target bid {target_bid} PASSED the keyword filter and would be included in Excel!")
        else:
            print(f"[FILTERED OUT] Target bid {target_bid} was DROPPED by the Keyword Filter.")
            print("Reason: None of the terms in the title/category matched your config/keywords.json terms.")
    else:
        print("[SKIPPED] Cannot test keyword filter because the bid wasn't returned by the GeM collector API.")

    print("\n==================================================")
    print("TEST COMPLETED")
    print("==================================================")

if __name__ == "__main__":
    test_gem_collection()