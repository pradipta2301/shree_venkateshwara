from app.collectors.odisha_portal_collector import OdishaPortalCollector

print("Initializing Odisha Govt Portal Collector...")
collector = OdishaPortalCollector()
tenders = collector.collect()

print(f"\nTotal Records Found: {len(tenders)}")
for i, t in enumerate(tenders[:5]):
    print(f"\n{i+1}. Tender No: {t.tender_no}")
    print(f"   Title: {t.title[:70]}...")
    print(f"   Closing Date: {t.closing_date}")
    print(f"   Link: {t.link}")