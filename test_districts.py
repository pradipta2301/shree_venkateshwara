import os
import datetime
import json
from app.collectors.odisha_districts import OdishaDistrictCollector
from app.exporters.excel_exporter import export_to_excel

def extract_flat_keywords(json_file="config/keywords.json"):
    """Extracts all keywords from the nested JSON into a single flat list."""
    keywords = []
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        for category, subcategories in data.items():
            for product, synonyms in subcategories.items():
                for word in synonyms:
                    keywords.append(word.lower().strip())
    except Exception as e:
        print(f"Error reading keywords.json: {e}")
    return keywords

def main():
    print()
    print("======================================")
    print("   DISTRICT TENDERS BRUTE-FORCE TEST")
    print("======================================")
    print()

    # STEP 1: Collect raw tenders
    print("Starting extraction from District Portals...")
    collector = OdishaDistrictCollector(config_path="config/websites.json")
    district_tenders = collector.collect()

    print("\n======================================")
    print(f"TOTAL RAW DISTRICT TENDERS COLLECTED: {len(district_tenders)}")
    print("======================================")

    if not district_tenders:
        return

    # STEP 2: Load our raw keywords list
    flat_keywords = extract_flat_keywords()
    print(f"Loaded {len(flat_keywords)} total keywords to search against.")

    # STEP 3: Brute-force substring match
    print("\nFiltering using raw text matching...")
    relevant_district_tenders = []
    
    for tender in district_tenders:
        title_lower = tender.title.lower()
        matched = False
        
        for kw in flat_keywords:
            if kw in title_lower:
                relevant_district_tenders.append(tender)
                print(f"  [MATCH] '{kw}' found in -> {tender.title}")
                matched = True
                break # Stop searching this title once it matches

    print("\n======================================")
    print(f"MATCHED DISTRICT TENDERS: {len(relevant_district_tenders)} / {len(district_tenders)}")
    print("======================================")

    # STEP 4: Export to Excel
    if relevant_district_tenders:
        os.makedirs("output", exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_filename = f"output/district_tenders_test_{timestamp}.xlsx"
        try:
            export_to_excel(relevant_district_tenders, excel_filename)
            print(f"\nReport generated successfully: {excel_filename}")
        except Exception as e:
            print(f"\n[ERROR] Failed to generate Excel report: {e}")
    else:
        print("\nStill 0 matches. The titles genuinely do not contain our keywords.")

if __name__ == "__main__":
    main()