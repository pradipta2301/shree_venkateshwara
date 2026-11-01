import sys
import os

# Add root directory to path so python can locate 'app' modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.collectors.urban_transport_collector import UrbanTransportCollector

def run_test():
    print("======================================")
    print("   TESTING URBAN TRANSPORT COLLECTOR")
    print("======================================")
    
    collector = UrbanTransportCollector()
    tenders = collector.collect()
    
    print(f"\nSuccessfully collected {len(tenders)} total tender/document records.")
    
    # Print sample extracted tenders
    for i, t in enumerate(tenders[:5], 1):
        print(f"\n{i}. Tender No: {t.tender_no}")
        print(f"   Department: {t.department}")
        print(f"   Title: {t.title[:75]}...")
        print(f"   Closing Date: {t.closing_date}")
        print(f"   PDF Link: {t.link}")

if __name__ == "__main__":
    run_test()