from dataclasses import dataclass


@dataclass
class Tender:

    # ============================================================
    # BASIC INFORMATION
    # ============================================================

    source: str
    tender_no: str
    title: str
    department: str
    closing_date: str
    link: str

    category: str = ""
    district: str = ""
    address: str = ""
    state: str = "Odisha"

    # ============================================================
    # BASIC GEM INFORMATION
    # ============================================================

    quantity: str = ""
    bid_type: str = ""
    buyer_name: str = ""

    tender_type: str = ""

    published_date: str = ""
    opening_date: str = ""

    # ============================================================
    # FINANCIAL INFORMATION
    # ============================================================

    tender_value: str = ""
    budget: str = ""
    emd: str = ""

    # ============================================================
    # ELIGIBILITY
    # ============================================================

    emd_eligibility: str = ""
    oem_requirement: str = ""
    past_experience: str = ""
    turnover_requirement: str = ""

    # ============================================================
    # CORRIGENDUM, AI SUMMARY & DOCUMENTS
    # ============================================================

    corrigendum: str = ""
    summary: str = ""
    additional_documents: str = ""
    filter_status: str = ""

    # ============================================================
    # TRACKING
    # ============================================================

    first_seen: str = ""
    last_seen: str = ""

    # ============================================================
    # DATABASE TIMESTAMPS
    # ============================================================

    created_at: str = ""
    updated_at: str = ""

    # ============================================================
    # STATUS
    # ============================================================

    status: str = "Ongoing"