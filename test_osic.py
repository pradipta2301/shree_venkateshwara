from app.collectors.osic_collector import OSICCollector

print("Testing OSIC Collector...")
collector = OSICCollector()
tenders = collector.collect()

print(f"\nTotal Tenders Found: {len(tenders)}")
for i, t in enumerate(tenders[:5]):
    print(f"\n{i+1}. Tender No: {t.tender_no}")
    print(f"   Title: {t.title}")
    print(f"   Dates (Pub/Close): {t.published_date} / {t.closing_date}")
    print(f"   Link: {t.link}")