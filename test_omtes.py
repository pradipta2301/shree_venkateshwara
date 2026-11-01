from app.collectors.omtes_collector import OMTESCollector

print("Testing OMTES Collector...")
collector = OMTESCollector()
tenders = collector.collect()

print(f"\nTotal Tenders Found: {len(tenders)}")
for i, t in enumerate(tenders[:3]):
    print(f"\n{i+1}. Tender No: {t.tender_no}")
    print(f"   Title: {t.title}")
    print(f"   Closing: {t.closing_date}")
    print(f"   Link: {t.link}")