import sqlite3
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd


class Database:
    """
    SQLite database manager for the Tender Automation project.
    Acts as the single source of truth for caching:
    - Stores Stage 1 metadata, Stage 2 OCR pre-filter status ('PASSED' / 'DROPPED'),
      and Stage 3 AI deep extraction ('EXTRACTED').
    - Safely migrates existing data/tenders.db to include address, summary,
      additional_documents, and filter_status.
    """

    def __init__(self, db_path: str = "data/tenders.db"):
        self.db_path = db_path
        directory = os.path.dirname(self.db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        self.create_table()
        self.migrate_database()

    # ============================================================
    # DATABASE CONNECTION
    # ============================================================

    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ============================================================
    # CREATE TABLE
    # ============================================================

    def create_table(self):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tenders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                source TEXT,
                tender_no TEXT UNIQUE,
                title TEXT,
                department TEXT,
                buyer_name TEXT,

                category TEXT,
                district TEXT,
                state TEXT,
                address TEXT,

                quantity TEXT,
                tender_value TEXT,
                budget TEXT,
                emd TEXT,

                emd_eligibility TEXT,
                oem_requirement TEXT,
                past_experience TEXT,
                turnover_requirement TEXT,

                tender_type TEXT,
                bid_type TEXT,

                published_date TEXT,
                opening_date TEXT,
                closing_date TEXT,

                corrigendum TEXT,
                summary TEXT,
                additional_documents TEXT,
                filter_status TEXT DEFAULT '',

                status TEXT,
                link TEXT,

                first_seen TEXT,
                last_seen TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.commit()
        conn.close()

    # ============================================================
    # DATABASE MIGRATION (SAFE FOR EXISTING DB)
    # ============================================================

    def migrate_database(self):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(tenders)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        required_columns = {
            "buyer_name": "TEXT",
            "address": "TEXT",
            "quantity": "TEXT",
            "tender_value": "TEXT",
            "budget": "TEXT",
            "emd": "TEXT",
            "emd_eligibility": "TEXT",
            "oem_requirement": "TEXT",
            "past_experience": "TEXT",
            "turnover_requirement": "TEXT",
            "tender_type": "TEXT",
            "bid_type": "TEXT",
            "published_date": "TEXT",
            "opening_date": "TEXT",
            "closing_date": "TEXT",
            "corrigendum": "TEXT",
            "summary": "TEXT",
            "additional_documents": "TEXT",
            "filter_status": "TEXT DEFAULT ''",
            "first_seen": "TEXT",
            "last_seen": "TEXT",
            "updated_at": "TIMESTAMP",
        }

        for column, data_type in required_columns.items():
            if column not in existing_columns:
                try:
                    cursor.execute(
                        f"ALTER TABLE tenders ADD COLUMN {column} {data_type}"
                    )
                    print(f"Database migration: added column {column}")
                except Exception as exc:
                    print(f"Could not add column {column}: {exc}")

        conn.commit()
        conn.close()

    # ============================================================
    # SAFE ATTRIBUTE HELPER
    # ============================================================

    @staticmethod
    def value(obj, attribute: str, default: str = "") -> str:
        try:
            val = getattr(obj, attribute, default)
        except Exception:
            return default
        if val is None:
            return default
        return str(val).strip()

    # ============================================================
    # SAVE / UPSERT SINGLE TENDER (NEVER OVERWRITES EXTRACTED DATA WITH BLANKS)
    # ============================================================

    def save_tender(self, tender, filter_status: Optional[str] = None) -> bool:
        tender_no = self.value(tender, "tender_no", "")
        if not tender_no:
            return False

        now = datetime.now().isoformat(timespec="seconds")
        first_seen = self.value(tender, "first_seen", "") or now
        last_seen = self.value(tender, "last_seen", "") or now
        f_status = filter_status if filter_status is not None else self.value(tender, "filter_status", "")

        values = (
            self.value(tender, "source"),
            tender_no,
            self.value(tender, "title"),
            self.value(tender, "department"),
            self.value(tender, "buyer_name"),
            self.value(tender, "category"),
            self.value(tender, "district"),
            self.value(tender, "state", "Odisha"),
            self.value(tender, "address"),
            self.value(tender, "quantity"),
            self.value(tender, "tender_value"),
            self.value(tender, "budget"),
            self.value(tender, "emd"),
            self.value(tender, "emd_eligibility"),
            self.value(tender, "oem_requirement"),
            self.value(tender, "past_experience"),
            self.value(tender, "turnover_requirement"),
            self.value(tender, "tender_type"),
            self.value(tender, "bid_type"),
            self.value(tender, "published_date"),
            self.value(tender, "opening_date"),
            self.value(tender, "closing_date"),
            self.value(tender, "corrigendum"),
            self.value(tender, "summary"),
            self.value(tender, "additional_documents"),
            f_status,
            self.value(tender, "status", "Ongoing"),
            self.value(tender, "link"),
            first_seen,
            last_seen,
        )

        conn = self.connect()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO tenders (
                    source, tender_no, title, department, buyer_name,
                    category, district, state, address,
                    quantity, tender_value, budget, emd,
                    emd_eligibility, oem_requirement, past_experience, turnover_requirement,
                    tender_type, bid_type,
                    published_date, opening_date, closing_date,
                    corrigendum, summary, additional_documents, filter_status,
                    status, link, first_seen, last_seen
                )
                VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?
                )
                ON CONFLICT(tender_no) DO UPDATE SET
                    source = COALESCE(NULLIF(excluded.source, ''), tenders.source),
                    title = COALESCE(NULLIF(excluded.title, ''), tenders.title),
                    department = COALESCE(NULLIF(excluded.department, ''), tenders.department),
                    buyer_name = COALESCE(NULLIF(excluded.buyer_name, ''), tenders.buyer_name),
                    category = COALESCE(NULLIF(excluded.category, ''), tenders.category),
                    district = COALESCE(NULLIF(excluded.district, ''), tenders.district),
                    state = COALESCE(NULLIF(excluded.state, ''), tenders.state),
                    address = COALESCE(NULLIF(excluded.address, ''), tenders.address),
                    quantity = COALESCE(NULLIF(excluded.quantity, ''), tenders.quantity),
                    tender_value = COALESCE(NULLIF(excluded.tender_value, ''), tenders.tender_value),
                    budget = COALESCE(NULLIF(excluded.budget, ''), tenders.budget),
                    emd = COALESCE(NULLIF(excluded.emd, ''), tenders.emd),
                    emd_eligibility = COALESCE(NULLIF(excluded.emd_eligibility, ''), tenders.emd_eligibility),
                    oem_requirement = COALESCE(NULLIF(excluded.oem_requirement, ''), tenders.oem_requirement),
                    past_experience = COALESCE(NULLIF(excluded.past_experience, ''), tenders.past_experience),
                    turnover_requirement = COALESCE(NULLIF(excluded.turnover_requirement, ''), tenders.turnover_requirement),
                    tender_type = COALESCE(NULLIF(excluded.tender_type, ''), tenders.tender_type),
                    bid_type = COALESCE(NULLIF(excluded.bid_type, ''), tenders.bid_type),
                    published_date = COALESCE(NULLIF(excluded.published_date, ''), tenders.published_date),
                    opening_date = COALESCE(NULLIF(excluded.opening_date, ''), tenders.opening_date),
                    closing_date = COALESCE(NULLIF(excluded.closing_date, ''), tenders.closing_date),
                    corrigendum = COALESCE(NULLIF(excluded.corrigendum, ''), tenders.corrigendum),
                    summary = COALESCE(NULLIF(excluded.summary, ''), tenders.summary),
                    additional_documents = COALESCE(NULLIF(excluded.additional_documents, ''), tenders.additional_documents),
                    filter_status = COALESCE(NULLIF(excluded.filter_status, ''), tenders.filter_status),
                    status = COALESCE(NULLIF(excluded.status, ''), tenders.status),
                    link = COALESCE(NULLIF(excluded.link, ''), tenders.link),
                    last_seen = excluded.last_seen,
                    updated_at = CURRENT_TIMESTAMP
                """,
                values
            )
            conn.commit()
            return True
        except Exception as exc:
            print(f"Database error saving {tender_no}: {exc}")
            return False
        finally:
            conn.close()

    # ============================================================
    # SAVE MULTIPLE TENDERS
    # ============================================================

    def save_tenders(self, tenders: List[Any], filter_status: Optional[str] = None) -> int:
        saved = 0
        for tender in tenders:
            if self.save_tender(tender, filter_status=filter_status):
                saved += 1
        return saved

    # ============================================================
    # FAST IN-MEMORY CACHE LOADER (FOR ENGINE SKIP LOGIC)
    # ============================================================

    def get_cached_map(self) -> Dict[str, Dict[str, Any]]:
        """
        Loads all tenders from SQLite into a fast lookup dictionary.
        Keys include both `tender_no` and `link` so even tenders with
        generic numbers can be matched immediately without re-downloading PDFs.
        """
        cache_map: Dict[str, Dict[str, Any]] = {}
        conn = self.connect()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM tenders")
            rows = cursor.fetchall()
            for row in rows:
                record = dict(row)
                t_no = str(record.get("tender_no") or "").strip()
                link = str(record.get("link") or "").strip()

                if t_no and t_no not in ("NIC-UNKNOWN", "ODISHA-GOV-UNKNOWN", "OCAC-UNKNOWN", "OMTES-UNKNOWN"):
                    cache_map[t_no] = record
                if link and link.startswith("http"):
                    cache_map[link] = record
        except Exception as exc:
            print(f"Could not load DB cache map: {exc}")
        finally:
            conn.close()

        return cache_map

    # ============================================================
    # SEED DATABASE FROM EXISTING EXCEL (ONE-TIME SYNC)
    # ============================================================

    def import_from_excel(self, excel_path: str) -> int:
        """
        Seeds the SQLite database with previously extracted rows from
        odisha_tenders.xlsx so already-processed tenders are marked 'EXTRACTED'
        and never re-downloaded.
        """
        if not os.path.exists(excel_path):
            return 0

        try:
            df = pd.read_excel(excel_path).fillna("")
        except Exception as exc:
            print(f"  [DB Seed] Could not read {excel_path}: {exc}")
            return 0

        conn = self.connect()
        cursor = conn.cursor()
        imported = 0
        now = datetime.now().isoformat(timespec="seconds")

        for _, row in df.iterrows():
            t_no = str(row.get("Tender No", "")).strip()
            if not t_no:
                continue

            cursor.execute(
                """
                INSERT INTO tenders (
                    source, tender_no, title, department, buyer_name,
                    category, district, state, address,
                    quantity, tender_value, budget, emd,
                    emd_eligibility, oem_requirement, past_experience, turnover_requirement,
                    tender_type, bid_type,
                    published_date, opening_date, closing_date,
                    corrigendum, summary, additional_documents, filter_status,
                    status, link, first_seen, last_seen
                )
                VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, 'EXTRACTED',
                    ?, ?, ?, ?
                )
                ON CONFLICT(tender_no) DO UPDATE SET
                    summary = COALESCE(NULLIF(excluded.summary, ''), tenders.summary),
                    address = COALESCE(NULLIF(excluded.address, ''), tenders.address),
                    district = COALESCE(NULLIF(excluded.district, ''), tenders.district),
                    tender_value = COALESCE(NULLIF(excluded.tender_value, ''), tenders.tender_value),
                    emd = COALESCE(NULLIF(excluded.emd, ''), tenders.emd),
                    additional_documents = COALESCE(NULLIF(excluded.additional_documents, ''), tenders.additional_documents),
                    filter_status = 'EXTRACTED'
                """,
                (
                    str(row.get("Source", "")),
                    t_no,
                    str(row.get("Title", "")),
                    str(row.get("Department", "")),
                    str(row.get("Buyer Name", "")),
                    str(row.get("Category", "")),
                    str(row.get("District", "")),
                    str(row.get("State", "Odisha")),
                    str(row.get("Address", "")),
                    str(row.get("Quantity", "")),
                    str(row.get("Tender Value", "")),
                    str(row.get("Budget", "")),
                    str(row.get("EMD", "")),
                    str(row.get("EMD Eligibility", "")),
                    str(row.get("OEM Requirement", "")),
                    str(row.get("Past Experience", "")),
                    str(row.get("Turnover Requirement", "")),
                    str(row.get("Tender Type", "")),
                    str(row.get("Bid Type", "")),
                    str(row.get("Published Date", "")),
                    str(row.get("Opening Date", "")),
                    str(row.get("Closing Date", "")),
                    str(row.get("Corrigendum", "")),
                    str(row.get("Summary", "")),
                    str(row.get("Additional Documents", "")),
                    str(row.get("Status", "Ongoing")),
                    str(row.get("Link", "")),
                    now,
                    now,
                )
            )
            imported += 1

        conn.commit()
        conn.close()
        return imported

    # ============================================================
    # APPLY DB RECORD TO TENDER OBJECT IN MEMORY
    # ============================================================

    @staticmethod
    def hydrate_tender_from_record(tender, record: Dict[str, Any]):
        """
        Copies all enriched fields from a SQLite row dictionary onto a Tender object.
        """
        fields = [
            "district", "address", "quantity", "tender_value", "budget",
            "emd", "emd_eligibility", "oem_requirement", "past_experience",
            "turnover_requirement", "tender_type", "bid_type",
            "published_date", "opening_date", "closing_date",
            "corrigendum", "summary", "additional_documents"
        ]
        for field in fields:
            db_val = str(record.get(field) or "").strip()
            if db_val:
                setattr(tender, field, db_val)
        return tender

    # ============================================================
    # GET ALL TENDERS / COUNTS
    # ============================================================

    def get_all_tenders(self):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tenders ORDER BY closing_date ASC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def count_tenders(self) -> int:
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tenders")
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_tender(self, tender_no: str) -> Optional[Dict[str, Any]]:
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tenders WHERE tender_no = ?", (tender_no,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None