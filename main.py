import json
import os
from typing import Dict, Any, Optional

from dotenv import load_dotenv
load_dotenv()

# Import Registry, Database, and Engine
from app.core.registry import registry
from app.database.database import Database
from app.core.engine import TenderEngine

# Import all collectors
from app.collectors.gem import GeMCollector
from app.collectors.odisha_districts import OdishaDistrictCollector
from app.collectors.ocac_collector import OCACCollector
from app.collectors.tendersodisha_collector import TendersOdishaCollector
from app.collectors.odisha_portal_collector import OdishaPortalCollector
from app.collectors.urban_transport_collector import UrbanTransportCollector
from app.collectors.omtes_collector import OMTESCollector
from app.collectors.osic_collector import OSICCollector
from app.collectors.stsc_collector import STSCCollector

# ==================================================
# REGISTER COLLECTORS
# ==================================================
registry.register("gem", GeMCollector, collector_type="standard")
registry.register("districts", OdishaDistrictCollector, collector_type="district")
registry.register("ocac", OCACCollector, collector_type="standard")
registry.register("tenders_odisha", TendersOdishaCollector, collector_type="standard")
registry.register("odisha_portal", OdishaPortalCollector, collector_type="standard")
registry.register("urban_transport", UrbanTransportCollector, collector_type="standard")
registry.register("omtes", OMTESCollector, collector_type="standard")
registry.register("osic", OSICCollector, collector_type="standard")
registry.register("stsc", STSCCollector, collector_type="district")


class CacheManager:
    """
    Unified SQLite + Excel Cache Manager.
    Seeds SQLite from existing odisha_tenders.xlsx on startup and serves
    instant in-memory lookups by both tender_no and link.
    """
    def __init__(
        self,
        output_path: str = r"E:\TenderAutomation\output\odisha_tenders.xlsx",
        history_path: str = r"E:\TenderAutomation\output\district_history_cache.json",
        db_path: str = "data/tenders.db"
    ):
        self.output_path = output_path
        self.history_path = history_path
        self.db = Database(db_path)
        self.cached_data: Dict[str, Dict[str, Any]] = {}
        self.district_history: Dict[str, str] = {}
        self._initialize_cache()

    def _initialize_cache(self):
        # 1. Seed SQLite DB from existing Excel if present so historical AI runs aren't lost
        if os.path.exists(self.output_path):
            seeded = self.db.import_from_excel(self.output_path)
            if seeded:
                print(f"  [DB Cache] Synced {seeded} existing tenders from Excel into SQLite.")

        # 2. Load existing district 1st-page OCR history cache (PASSED / DROPPED)
        if os.path.exists(self.history_path):
            try:
                with open(self.history_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.district_history = data
                print(f"  [DB Cache] Loaded {len(self.district_history)} District OCR pre-filter history records.")
            except Exception as e:
                print(f"  [DB Cache] Warning: Could not load district history JSON: {e}")

        # 3. Load fast in-memory lookup map from SQLite (indexed by tender_no and link)
        self.cached_data = self.db.get_cached_map()
        print(f"  [DB Cache] Ready with {len(self.cached_data)} cached keys in memory.")

    def get_cached_record(self, tender_no: str, link: str = "") -> Optional[Dict[str, Any]]:
        """Returns the full SQLite row dictionary if the tender was already processed."""
        if tender_no and tender_no in self.cached_data:
            return self.cached_data[tender_no]
        if link and link in self.cached_data:
            return self.cached_data[link]
        return None

    def is_extracted(self, tender_no: str, link: str = "") -> bool:
        """Returns True if Stage 3 extraction/AI was already completed for this tender."""
        rec = self.get_cached_record(tender_no, link)
        if not rec:
            return False
        if rec.get("filter_status") == "EXTRACTED":
            return True
        if rec.get("summary") or rec.get("tender_value") or rec.get("emd") or rec.get("address"):
            return True
        return False

    def get_district_prefilter_status(self, tender_no: str, link: str = "") -> str:
        """
        Checks whether a District/STSC tender already PASSED or DROPPED
        Stage 2 1st-page OCR pre-filtering in SQLite or district_history_cache.json.
        """
        rec = self.get_cached_record(tender_no, link)
        if rec:
            f_status = str(rec.get("filter_status") or "").upper()
            if f_status in ("PASSED", "DROPPED", "EXTRACTED"):
                return f_status
            if rec.get("summary") or rec.get("tender_value") or rec.get("emd"):
                return "EXTRACTED"

        if tender_no and tender_no in self.district_history:
            return self.district_history[tender_no]
        if link and link in self.district_history:
            return self.district_history[link]
        return ""

    def record_district_prefilter(self, tender, status: str):
        """Persists Stage 2 District OCR pre-filter result immediately to both SQLite and JSON."""
        self.district_history[tender.tender_no] = status
        if tender.link:
            self.district_history[tender.link] = status
        self.db.save_tender(tender, filter_status=status)
        self.cached_data[tender.tender_no] = self.db.get_tender(tender.tender_no) or {}
        if tender.link:
            self.cached_data[tender.link] = self.cached_data[tender.tender_no]

    def save_district_history_file(self):
        try:
            os.makedirs(os.path.dirname(self.history_path), exist_ok=True)
            with open(self.history_path, "w", encoding="utf-8") as f:
                json.dump(self.district_history, f, indent=4)
        except Exception as e:
            print(f"  [Warning] Could not save district history cache: {e}")


def load_district_master(config_path: str = "config/keywords.json") -> list:
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("odisha_districts_master", [])
    except Exception as e:
        print(f"Error loading district master from {config_path}: {e}")
        return []


def main():
    master_districts = load_district_master("config/keywords.json")
    cache_manager = CacheManager(
        output_path=r"E:\TenderAutomation\output\odisha_tenders.xlsx",
        history_path=r"E:\TenderAutomation\output\district_history_cache.json",
        db_path="data/tenders.db"
    )

    engine = TenderEngine(cache_manager=cache_manager, master_districts=master_districts)
    engine.run_pipeline()


if __name__ == "__main__":
    main()