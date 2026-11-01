import json
from app.collectors.gem import GeMCollector
from app.filters.keyword_filter import KeywordFilter
from app.database.database import Database

def main():
    target_tender_no = "GEM/2026/B/7940766"
    print(f"\n======================================")
    print(f"  GEM TENDER DIAGNOSTIC: {target_tender_no}")
    print("======================================")

    # 1. Check SQLite Database / Cache First
    db = Database()
    db_row = db.get_tender(target_tender_no)
    if db_row:
        print(f"\n[FOUND IN DB] Tender exists in database:")
        print(f"  - Title: {db_row[3]}")
        print(f"  - Department: {db_row[4]}")
        print(f"  - District: {db_row[6]}")
        print(f"  - Link: {db_row[23]}")
    else:
        print(f"\n[NOT IN DB] Tender {target_tender_no} is not present in SQLite database.")

    # 2. Run GeM Collector to see if API returns it
    print("\n[COLLECTOR CHECK] Fetching recent Odisha tenders from GeM API...")
    gem_collector = GeMCollector()
    gem_tenders = gem_collector.collect()
    print(f"Total Odisha tenders pulled from GeM API: {len(gem_tenders)}")

    # Look for our specific target in collected items
    target_tender = next((t for t in gem_tenders if t.tender_no == target_tender_no), None)

    if target_tender:
        print(f"\n[SUCCESS] Tender {target_tender_no} WAS FOUND by GeMCollector!")
        print(f"  - Title: {target_tender.title}")
        print(f"  - Department: {target_tender.department}")
        print(f"  - District: {target_tender.district}")
        
        # 3. Test Keyword Filter
        print("\n[FILTER CHECK] Testing against KeywordFilter...")
        kw_filter = KeywordFilter("config/keywords.json")
        filtered_list = kw_filter.filter([target_tender])
        
        if filtered_list:
            print(f"  -> [PASSED] Tender passed the Keyword Filter and is relevant!")
        else:
            print(f"  -> [FILTERED OUT] Tender was DROPPED by KeywordFilter. Check your config/keywords.json terms.")
    else:
        print(f"\n[MISSING FROM API] Tender {target_tender_no} was NOT returned by GeMCollector.")
        print("  Possible Reasons:")
        print("  1. Pagination limit: The tender is older or deeper down than the current API fetch limit allows.")
        print("  2. State Query mismatch: GeM API search parameters for 'Odisha' did not include this office/district.")

if __name__ == "__main__":
    main()