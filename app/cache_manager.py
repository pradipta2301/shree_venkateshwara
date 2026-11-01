import os
import pandas as pd
from typing import Dict, Any

class CacheManager:
    """
    Manages caching of previously extracted tenders in odisha_tenders.xlsx
    to avoid redundant PDF downloads and AI API calls.
    """
    def __init__(self, output_path: str = r"E:\TenderAutomation\output\odisha_tenders.xlsx"):
        self.output_path = output_path
        self.cached_data: Dict[str, Dict[str, Any]] = {}
        self._load_cache()

    def _load_cache(self):
        """Reads the existing master excel file and creates a lookup dictionary by tender_no."""
        if not os.path.exists(self.output_path):
            print(f"  [Cache] No existing cache found at {self.output_path}. Starting fresh.")
            return

        try:
            # Read Excel file[cite: 6]
            df = pd.read_excel(self.output_path)
            
            # Normalize column names to handle both old and new schema variations smoothly
            df.columns = [str(col).strip() for col in df.columns]
            
            # Check if tender_no or Tender No column exists
            id_col = 'Tender No' if 'Tender No' in df.columns else ('tender_no' if 'tender_no' in df.columns else None)
            
            if id_col:
                df = df.fillna("")
                for _, row in df.iterrows():
                    tender_no = str(row[id_col]).strip()
                    if tender_no and tender_no != "NIC-UNKNOWN" and tender_no != "ODISHA-GOV-UNKNOWN":
                        # Store all column values as a dictionary[cite: 6]
                        self.cached_data[tender_no] = row.to_dict()
                        
                print(f"  [Cache] Successfully loaded {len(self.cached_data)} previously extracted tenders from cache[cite: 6].")
            else:
                print("  [Cache] Existing file found, but 'Tender No' column is missing. Starting fresh[cite: 6].")
        except Exception as e:
            print(f"  [Cache] Warning: Could not load cache file: {e}[cite: 6]")

    def get_cached_tender(self, tender_no: str) -> Dict[str, Any]:
        """Returns cached data if it exists and has an AI summary[cite: 6]."""
        if tender_no and tender_no in self.cached_data:
            cached = self.cached_data[tender_no]
            # Check fields across both title-case and lowercase schemas
            if cached.get("Summary") or cached.get("summary") or cached.get("District") or cached.get("district") or cached.get("Tender Value"):
                return cached
        return {}