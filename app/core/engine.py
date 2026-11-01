import os
import json
import time
import hashlib
import subprocess
from datetime import datetime
import requests
from typing import List, Dict, Any
from app.core.registry import registry
from app.database.database import Database
from app.exporters.excel_exporter import export_to_excel
from app.exporters.web_exporter import export_to_web
from app.filters.keyword_filter import KeywordFilter
from app.collectors.district_document_extractor import DistrictDocumentExtractor
from app.collectors.gem_document_extractor import GeMDocumentExtractor
from app.collectors.ai_document_extractor import AIDocumentExtractor
from app.collectors.tendersodisha_collector import TendersOdishaCollector
from app.notifications.email_notifier import send_email_alert
from app.notifications.whatsapp_notifier import send_whatsapp_alert

UNKNOWN_TENDER_IDS = {
    "NIC-UNKNOWN",
    "ODISHA-GOV-UNKNOWN",
    "OCAC-UNKNOWN",
    "OMTES-UNKNOWN",
    "UNKNOWN",
    "NA",
    "N/A",
    ""
}


class TenderEngine:
    def __init__(self, cache_manager, master_districts: List[str]):
        self.cache_manager = cache_manager
        self.master_districts = master_districts
        self.db: Database = cache_manager.db
        self.keyword_filter = KeywordFilter("config/keywords.json")
        self.ai_extractor = AIDocumentExtractor()
        self.district_extractor = DistrictDocumentExtractor()
        self.gem_extractor = GeMDocumentExtractor()
        self.nic_collector = TendersOdishaCollector()
        self.github_repo_dir = os.environ.get("GITHUB_REPO_DIR", r"E:\TenderAutomation")

    @staticmethod
    def ensure_unique_tender_no(tender) -> None:
        """
        Replaces placeholder tender numbers (like ODISHA-GOV-UNKNOWN or NIC-UNKNOWN)
        with a deterministic hash based on the PDF link or title so SQLite can cache them.
        """
        raw_no = str(getattr(tender, "tender_no", "") or "").strip()
        if raw_no.upper() in UNKNOWN_TENDER_IDS:
            seed = f"{getattr(tender, 'link', '')}|{getattr(tender, 'title', '')}"
            short_hash = hashlib.md5(seed.encode("utf-8")).hexdigest()[:8].upper()
            prefix = str(getattr(tender, "source", "TND"))[:4].upper().replace(" ", "")
            tender.tender_no = f"{prefix}-{short_hash}"

    def sync_to_github(self, files_to_sync: List[str]) -> None:
        """
        Stages, commits, and pushes updated Excel and standalone website files to GitHub.
        """
        print("\n======================================")
        print("SYNCING EXCEL & WEBSITE TO GITHUB")
        print("======================================")
        try:
            for file_path in files_to_sync:
                if file_path and os.path.exists(file_path):
                    subprocess.run(
                        ["git", "add", "-f", file_path],
                        cwd=self.github_repo_dir,
                        check=True,
                        capture_output=True,
                        text=True
                    )

            status = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                cwd=self.github_repo_dir
            )
            if status.returncode == 0:
                print("  [GitHub Sync] No changes detected in output files. Skipping push.")
                return

            timestamp = datetime.now().strftime("%d-%b-%Y %I:%M %p")
            commit_msg = f"Auto-update Odisha Tenders & Web Portal ({timestamp})"
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=self.github_repo_dir,
                check=True,
                capture_output=True,
                text=True
            )

            subprocess.run(
                ["git", "pull", "--rebase"],
                cwd=self.github_repo_dir,
                check=False,
                capture_output=True,
                text=True
            )

            subprocess.run(
                ["git", "push"],
                cwd=self.github_repo_dir,
                check=True,
                capture_output=True,
                text=True
            )
            print(f"  [GitHub Sync SUCCESS] Pushed to GitHub: {commit_msg}")

        except subprocess.CalledProcessError as e:
            print(f"  [GitHub Sync ERROR] Git command failed: {e.stderr or e}")
        except Exception as e:
            print(f"  [GitHub Sync ERROR] Unexpected error: {e}")

    def run_pipeline(self):
        print("\n======================================")
        print("     TENDER INTELLIGENCE PLATFORM")
        print("======================================")

        # Track existing extracted tender numbers before this run starts (for new alert detection)
        previously_extracted_nos = {
            k for k, v in self.cache_manager.cached_data.items()
            if v.get("filter_status") == "EXTRACTED" or v.get("summary") or v.get("tender_value")
        }

        standard_tenders = []
        district_tenders = []

        # ==================================================
        # STAGE 1: COLLECTION FROM REGISTRY
        # ==================================================
        for name, info in registry.get_all_collectors().items():
            try:
                print(f"\nStarting Collection from [{name}]...")
                collector_instance = info["class"]()
                tenders = collector_instance.collect()
                for t in tenders:
                    self.ensure_unique_tender_no(t)

                print(f"Collected {len(tenders)} tenders from {name}.")

                if info["type"] == "district":
                    district_tenders.extend(tenders)
                else:
                    standard_tenders.extend(tenders)
            except Exception as e:
                print(f"Error collecting from {name}: {e}")

        all_collected_tenders = standard_tenders + district_tenders
        print(f"\nTotal Combined Tenders Collected: {len(all_collected_tenders)}")

        # ==================================================
        # STAGE 2: FILTERING & FAST DB-CACHED DISTRICT PRE-FILTER
        # ==================================================
        print("\n======================================")
        print("KEYWORD FILTER & DISTRICT OCR PRE-FILTER")
        print("======================================")

        # 1. Filter standard sources normally
        filtered_standard_tenders = self.keyword_filter.filter(standard_tenders)

        # 2. Evaluate District / STSC tenders using SQLite + History Cache first
        filtered_district_tenders = []

        if district_tenders:
            print(f"\nEvaluating {len(district_tenders)} District/STSC Portal tenders (Using DB Cache)...")
            for tender in district_tenders:
                prev_status = self.cache_manager.get_district_prefilter_status(tender.tender_no, tender.link)

                if prev_status in ("PASSED", "EXTRACTED"):
                    print(f"  [DB CACHE HIT - PASSED] Skipping 1st-page OCR for: {tender.tender_no}")
                    filtered_district_tenders.append(tender)
                    continue
                elif prev_status == "DROPPED":
                    print(f"  [DB CACHE HIT - DROPPED] Skipping previously rejected tender: {tender.tender_no}")
                    continue

                # Only run 1st-page OCR if never seen before
                details = self.district_extractor.process_tender(tender.tender_no, tender.link, max_pages=1)
                raw_text = details.get("raw_text", "")

                if raw_text:
                    original_title = tender.title
                    tender.title = f"{original_title} {raw_text}"
                    matched = self.keyword_filter.filter([tender])
                    tender.title = original_title

                    if matched:
                        print(f"  [PASSED] Pre-Filter tender {tender.tender_no} matched keywords.")
                        filtered_district_tenders.append(tender)
                        self.cache_manager.record_district_prefilter(tender, "PASSED")
                    else:
                        print(f"  [DROPPED] Pre-Filter tender {tender.tender_no} did not match keywords.")
                        self.cache_manager.record_district_prefilter(tender, "DROPPED")
                else:
                    print(f"  [DROPPED] Pre-Filter tender {tender.tender_no} failed PDF download.")
                    self.cache_manager.record_district_prefilter(tender, "DROPPED")

            self.cache_manager.save_district_history_file()

        relevant_tenders = filtered_standard_tenders + filtered_district_tenders
        print(f"\nTotal Relevant Tenders after filtering: {len(relevant_tenders)}")

        # ==================================================
        # STAGE 3: DOCUMENT EXTRACTION & AI INTELLIGENCE (DB-SKIP ENABLED)
        # ==================================================
        if relevant_tenders:
            print("\nStarting Stage 3: Deep Document Intelligence & Custom Routing...\n")

            for i, tender in enumerate(relevant_tenders, 1):
                # Check SQLite DB first — if already extracted, hydrate in memory & skip PDF/AI!
                if self.cache_manager.is_extracted(tender.tender_no, tender.link):
                    cached_rec = self.cache_manager.get_cached_record(tender.tender_no, tender.link)
                    if cached_rec:
                        print(f"  [DB CACHE HIT {i}/{len(relevant_tenders)}] Skipping PDF & AI for: {tender.tender_no}")
                        self.db.hydrate_tender_from_record(tender, cached_rec)
                        continue

                raw_text = ""

                # Route 1: GeM API & OMTES Tenders
                if tender.source in ["GeM", "OMTES"]:
                    print(f"\nProcessing {tender.source} PDF {i}/{len(relevant_tenders)}: {tender.tender_no}")
                    details = self.gem_extractor.process_tender(tender.tender_no, tender.link)

                    if details:
                        raw_text = details.get("raw_text", "")
                        tender.quantity = details.get("quantity") or tender.quantity
                        tender.tender_value = details.get("tender_value") or tender.tender_value
                        tender.budget = details.get("budget") or tender.budget
                        tender.emd = details.get("emd") or tender.emd
                        tender.emd_eligibility = details.get("emd_eligibility") or tender.emd_eligibility
                        tender.oem_requirement = details.get("oem_requirement") or tender.oem_requirement
                        tender.past_experience = details.get("past_experience") or tender.past_experience
                        tender.turnover_requirement = details.get("turnover_requirement") or tender.turnover_requirement
                        tender.corrigendum = details.get("corrigendum") or tender.corrigendum
                        tender.address = details.get("address", "")

                        if not tender.published_date:
                            tender.published_date = details.get("published_date", "")
                        if not tender.opening_date:
                            tender.opening_date = details.get("opening_date", "")
                        if not tender.tender_type:
                            tender.tender_type = details.get("tender_type", "")
                        if details.get("district"):
                            tender.district = details.get("district")

                # Route 2: OSIC (Download PDF Locally, Bypass AI)
                elif tender.source == "OSIC":
                    print(f"\nProcessing OSIC {i}/{len(relevant_tenders)}: {tender.tender_no}")
                    print("  -> Downloading PDF locally. Skipping AI processing.")

                    try:
                        osic_pdf_dir = r"E:\TenderAutomation\output\pdfs\OSIC"
                        os.makedirs(osic_pdf_dir, exist_ok=True)

                        safe_filename = "".join(
                            [c for c in tender.tender_no if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]
                        ).rstrip()
                        pdf_path = os.path.join(osic_pdf_dir, f"{safe_filename}.pdf")

                        if not os.path.exists(pdf_path) and tender.link.startswith("http"):
                            resp = requests.get(tender.link, timeout=30, verify=False)
                            if resp.status_code == 200:
                                with open(pdf_path, 'wb') as f:
                                    f.write(resp.content)
                                print(f"  [SUCCESS] OSIC PDF saved to: {pdf_path}")
                            else:
                                print(f"  [WARNING] OSIC PDF download failed. HTTP {resp.status_code}")
                    except Exception as e:
                        print(f"  [ERROR] Failed to download OSIC PDF: {e}")

                    raw_text = ""
                    tender.summary = "OSIC Tender: PDF downloaded locally. Metadata captured from UI. AI Bypassed."

                # Route 3: TendersOdisha (NIC) Details Scraper
                elif tender.source == "TendersOdisha":
                    print(f"\nProcessing NIC Tender Details Page {i}/{len(relevant_tenders)}: {tender.tender_no}")
                    print("  -> Scraping Tender Details directly from HTML (No PDF download, No Captcha)...")
                    nic_data = self.nic_collector.extract_details(tender.link)

                    if nic_data:
                        if nic_data.get("emd"):
                            tender.emd = nic_data["emd"]
                        if nic_data.get("emd_eligibility"):
                            tender.emd_eligibility = nic_data["emd_eligibility"]
                        if nic_data.get("tender_value"):
                            tender.tender_value = nic_data["tender_value"]
                        if nic_data.get("tender_type"):
                            tender.tender_type = nic_data["tender_type"]
                        if nic_data.get("summary"):
                            tender.summary = nic_data["summary"]
                        if nic_data.get("page_url"):
                            tender.link = nic_data["page_url"]
                        print(f"  [NIC DETAILS EXTRACTED] EMD: ₹{tender.emd} | Value: ₹{tender.tender_value} | Type: {tender.tender_type}")

                    raw_text = ""

                # Route 4: District / Portal / Urban / STSC Tenders (OCR & AI)
                else:
                    print(f"\nProcessing Portal OCR/Web {i}/{len(relevant_tenders)}: {tender.tender_no}")
                    details = self.district_extractor.process_tender(tender.tender_no, tender.link, max_pages=10)

                    if details:
                        raw_text = details.get("raw_text", "")
                        if details.get("emd"):
                            tender.emd = details.get("emd")
                        if details.get("tender_value"):
                            tender.tender_value = details.get("tender_value")
                        if not tender.published_date and details.get("published_date"):
                            tender.published_date = details.get("published_date")
                        if not tender.closing_date and details.get("closing_date"):
                            tender.closing_date = details.get("closing_date")

                # Route 5: AI Deep Extraction (Only runs if raw_text is populated)
                if raw_text:
                    print(f"  -> Sending {len(raw_text):,} chars to AI Engine for deep analysis & summary...")
                    ai_data = self.ai_extractor.extract_tender_details(raw_text, source=tender.source)
                    if ai_data:
                        if ai_data.get("district"):
                            tender.district = ai_data.get("district")
                        if ai_data.get("address"):
                            tender.address = ai_data.get("address")
                        if ai_data.get("quantity"):
                            tender.quantity = ai_data.get("quantity")
                        if ai_data.get("tender_value"):
                            tender.tender_value = ai_data.get("tender_value")
                        if ai_data.get("budget"):
                            tender.budget = ai_data.get("budget")
                        if ai_data.get("emd"):
                            tender.emd = ai_data.get("emd")
                        if ai_data.get("emd_eligibility"):
                            tender.emd_eligibility = ai_data.get("emd_eligibility")
                        if ai_data.get("oem_requirement"):
                            tender.oem_requirement = ai_data.get("oem_requirement")
                        if ai_data.get("past_experience"):
                            tender.past_experience = ai_data.get("past_experience")
                        if ai_data.get("turnover_requirement"):
                            tender.turnover_requirement = ai_data.get("turnover_requirement")
                        if ai_data.get("tender_type"):
                            tender.tender_type = ai_data.get("tender_type")
                        if ai_data.get("corrigendum"):
                            tender.corrigendum = ai_data.get("corrigendum")
                        if ai_data.get("summary"):
                            tender.summary = ai_data.get("summary")
                        if ai_data.get("published_date"):
                            tender.published_date = ai_data.get("published_date")
                        if ai_data.get("opening_date"):
                            tender.opening_date = ai_data.get("opening_date")
                        if ai_data.get("closing_date"):
                            tender.closing_date = ai_data.get("closing_date")
                        print(f"  [AI SUMMARY ADDED] District: {tender.district} | EMD: {tender.emd}")

                if not getattr(tender, "summary", ""):
                    tender.summary = f"{tender.title} ({tender.department})"

                # Save immediately to SQLite as 'EXTRACTED' so progress is never lost
                self.db.save_tender(tender, filter_status="EXTRACTED")
                self.cache_manager.cached_data[tender.tender_no] = self.db.get_tender(tender.tender_no) or {}
                if tender.link:
                    self.cache_manager.cached_data[tender.link] = self.cache_manager.cached_data[tender.tender_no]

                time.sleep(1.5)

        # ==================================================
        # ALERTS, EXCEL EXPORT, WEBSITE DATA EXPORT & GITHUB SYNC
        # ==================================================
        truly_new_tenders = [
            t for t in relevant_tenders
            if t.tender_no not in previously_extracted_nos and t.link not in previously_extracted_nos
        ]

        print(f"\nAlert Check: Found {len(truly_new_tenders)} strictly new tenders to notify.")

        output_filename = r"E:\TenderAutomation\output\odisha_tenders.xlsx"
        github_root_excel = os.path.join(self.github_repo_dir, "odisha_tenders.xlsx")

        if relevant_tenders:
            print("\nCreating final Excel report & updating Custom Website feed...")
            try:
                saved_excel_files = export_to_excel(
                    relevant_tenders,
                    output_filename,
                    mirror_paths=[github_root_excel]
                )
                print(f"Excel master file updated successfully: {output_filename}")

                # Export JSON + HTML assets for the standalone custom website
                web_files = export_to_web(
                    relevant_tenders,
                    output_filename,
                    web_dir=self.github_repo_dir
                )

                files_to_push = list(set(saved_excel_files + web_files + [self.cache_manager.history_path]))
                self.sync_to_github(files_to_push)
            except PermissionError:
                print(f"FAILED: Please close Excel and try again. Could not write to {output_filename}")

        if truly_new_tenders:
            print("\nDispatching notifications for new tenders...")
            send_email_alert(truly_new_tenders)
            send_whatsapp_alert(truly_new_tenders)
        else:
            print("\n[Alerts] No new tenders found. Skipping email and WhatsApp alerts.")