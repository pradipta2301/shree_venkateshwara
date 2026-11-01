import json
import re
from typing import List, Tuple, Pattern
from app.models.tender import Tender

GENERIC_CATEGORIES = {
    "",
    "general",
    "na",
    "n/a",
    "state procurement",
    "state procurement / quotation",
    "it / electronics",
}


class KeywordFilter:
    def __init__(self, config_path: str = "config/keywords.json"):
        self.config_path = config_path
        # Stores tuples of (compiled_regex, product_subcategory_name, raw_keyword)
        self.compiled_rules: List[Tuple[Pattern, str, str]] = self._load_and_compile_keywords()

    def _load_and_compile_keywords(self) -> List[Tuple[Pattern, str, str]]:
        """
        Loads all keywords/synonyms from config/keywords.json and pre-compiles
        word-boundary regexes once at startup for fast matching and automatic
        product category tagging.
        """
        rules: List[Tuple[Pattern, str, str]] = []
        seen_keywords = set()

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for category, subcategories in data.items():
                # Only process dictionaries (skips 'odisha_districts_master' list)
                if isinstance(subcategories, dict):
                    for product_name, synonyms in subcategories.items():
                        if not isinstance(synonyms, list):
                            continue
                        for word in synonyms:
                            clean_word = " ".join(str(word).lower().strip().split())
                            if not clean_word or clean_word in seen_keywords:
                                continue
                            seen_keywords.add(clean_word)

                            # Use word boundaries on alphanumeric edges to prevent
                            # 'ups' matching 'groups' or 'ro system' matching 'micro systems'
                            pattern_str = r"(?<!\w)" + re.escape(clean_word) + r"(?!\w)"
                            compiled_pat = re.compile(pattern_str, flags=re.IGNORECASE)
                            rules.append((compiled_pat, product_name, clean_word))
        except Exception as e:
            print(f"Error reading {self.config_path}: {e}")

        return rules

    def filter(self, tenders: List[Tender]) -> List[Tender]:
        """
        Filters tenders against pre-compiled keyword patterns and automatically
        enriches generic tender categories with the matched product vertical
        (e.g., 'Smart Interactive Panel', 'Solar Lights', 'LLIN Mosquito Net').
        """
        relevant_tenders = []

        for tender in tenders:
            text_to_search = f"{tender.title} {tender.department} {tender.category}".lower()
            text_to_search = " ".join(text_to_search.split())

            for pattern, product_name, _ in self.compiled_rules:
                if pattern.search(text_to_search):
                    # Upgrade generic category labels to the specific product matched
                    current_cat = str(getattr(tender, "category", "") or "").strip().lower()
                    if current_cat in GENERIC_CATEGORIES:
                        tender.category = product_name
                    relevant_tenders.append(tender)
                    break

        return relevant_tenders