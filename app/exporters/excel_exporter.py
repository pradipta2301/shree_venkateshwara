import os
import re
import shutil
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from typing import List, Optional
from app.models.tender import Tender

# Regex pattern to catch invisible control characters (ASCII 0-31) that crash Excel
ILLEGAL_CHARACTERS_RE = re.compile(r'[\000-\010]|[\013-\014]|[\016-\037]')


def clean_excel_text(value) -> str:
    """Sanitizes text to prevent openpyxl IllegalCharacterError."""
    if value is None:
        return ""
    return ILLEGAL_CHARACTERS_RE.sub("", str(value)).strip()


def extract_extra_doc_links(tender: Tender) -> str:
    """
    Captures both tender.additional_documents and any extra PDF links
    stored inside tender.corrigendum (such as OCAC multi-volume RFPs).
    """
    add_docs = clean_excel_text(getattr(tender, "additional_documents", ""))
    if add_docs:
        return add_docs

    corrigendum = clean_excel_text(getattr(tender, "corrigendum", ""))
    if "http" in corrigendum:
        urls = re.findall(r'https?://[^\s|,]+', corrigendum)
        primary = clean_excel_text(getattr(tender, "link", ""))
        extra_urls = [u for u in urls if u != primary]
        if extra_urls:
            return ", ".join(extra_urls)
    return ""


def export_to_excel(
    tenders: List[Tender],
    filename: str,
    mirror_paths: Optional[List[str]] = None
) -> List[str]:
    """
    Exports a list of Tender objects to a formatted Excel file.
    Includes all Stage 1 (API), Stage 2 (PDF/OCR), AI Summary, Source, and Additional Documents.
    Automatically mirrors the file to root ('E:\\TenderAutomation\\odisha_tenders.xlsx')
    and returns the list of saved paths for GitHub sync.
    """
    dir_name = os.path.dirname(filename)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Tenders"

    # Headers (Includes "Source" and "Additional Documents" at the end)
    headers = [
        "Tender No",
        "Title",
        "Department",
        "Summary",
        "Category",
        "State",
        "District",
        "Address",
        "Quantity",
        "Tender Value",
        "Budget",
        "EMD",
        "EMD Eligibility",
        "OEM Requirement",
        "Past Experience",
        "Turnover Requirement",
        "Tender Type",
        "Bid Type",
        "Published Date",
        "Opening Date",
        "Closing Date",
        "Corrigendum",
        "Buyer Name",
        "Status",
        "Link",
        "Additional Documents",
        "Source"
    ]

    # Write and format headers
    header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Write data rows mapping the fields correctly
    for row_num, tender in enumerate(tenders, 2):
        ws.cell(row=row_num, column=1, value=clean_excel_text(getattr(tender, "tender_no", "")))
        ws.cell(row=row_num, column=2, value=clean_excel_text(getattr(tender, "title", "")))
        ws.cell(row=row_num, column=3, value=clean_excel_text(getattr(tender, "department", "")))
        ws.cell(row=row_num, column=4, value=clean_excel_text(getattr(tender, "summary", "")))
        ws.cell(row=row_num, column=5, value=clean_excel_text(getattr(tender, "category", "")))
        ws.cell(row=row_num, column=6, value=clean_excel_text(getattr(tender, "state", "Odisha")))
        ws.cell(row=row_num, column=7, value=clean_excel_text(getattr(tender, "district", "")))
        ws.cell(row=row_num, column=8, value=clean_excel_text(getattr(tender, "address", "")))
        ws.cell(row=row_num, column=9, value=clean_excel_text(getattr(tender, "quantity", "")))
        ws.cell(row=row_num, column=10, value=clean_excel_text(getattr(tender, "tender_value", "")))
        ws.cell(row=row_num, column=11, value=clean_excel_text(getattr(tender, "budget", "")))
        ws.cell(row=row_num, column=12, value=clean_excel_text(getattr(tender, "emd", "")))
        ws.cell(row=row_num, column=13, value=clean_excel_text(getattr(tender, "emd_eligibility", "")))
        ws.cell(row=row_num, column=14, value=clean_excel_text(getattr(tender, "oem_requirement", "")))
        ws.cell(row=row_num, column=15, value=clean_excel_text(getattr(tender, "past_experience", "")))
        ws.cell(row=row_num, column=16, value=clean_excel_text(getattr(tender, "turnover_requirement", "")))
        ws.cell(row=row_num, column=17, value=clean_excel_text(getattr(tender, "tender_type", "")))
        ws.cell(row=row_num, column=18, value=clean_excel_text(getattr(tender, "bid_type", "")))
        ws.cell(row=row_num, column=19, value=clean_excel_text(getattr(tender, "published_date", "")))
        ws.cell(row=row_num, column=20, value=clean_excel_text(getattr(tender, "opening_date", "")))
        ws.cell(row=row_num, column=21, value=clean_excel_text(getattr(tender, "closing_date", "")))
        ws.cell(row=row_num, column=22, value=clean_excel_text(getattr(tender, "corrigendum", "")))
        ws.cell(row=row_num, column=23, value=clean_excel_text(getattr(tender, "buyer_name", "")))
        ws.cell(row=row_num, column=24, value=clean_excel_text(getattr(tender, "status", "Ongoing")))
        ws.cell(row=row_num, column=25, value=clean_excel_text(getattr(tender, "link", "")))
        ws.cell(row=row_num, column=26, value=extract_extra_doc_links(tender))
        ws.cell(row=row_num, column=27, value=clean_excel_text(getattr(tender, "source", "")))

    # Auto-adjust column widths for readability
    for col in ws.columns:
        max_length = 0
        column_letter = col[0].column_letter
        for cell in col:
            try:
                if cell.value and len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except Exception:
                pass
        adjusted_width = min((max_length + 2), 50)
        ws.column_dimensions[column_letter].width = adjusted_width

    ws.freeze_panes = "A2"
    wb.save(filename)

    saved_paths = [os.path.abspath(filename)]

    # Mirror to root E:\TenderAutomation\odisha_tenders.xlsx and any passed mirror_paths
    default_root_excel = os.path.abspath(r"E:\TenderAutomation\odisha_tenders.xlsx")
    targets = [default_root_excel]
    if mirror_paths:
        targets.extend([os.path.abspath(p) for p in mirror_paths if p])

    for target_path in set(targets):
        if target_path != os.path.abspath(filename):
            try:
                target_dir = os.path.dirname(target_path)
                if target_dir:
                    os.makedirs(target_dir, exist_ok=True)
                shutil.copy2(filename, target_path)
                saved_paths.append(target_path)
                print(f"  [Excel Mirror] Synced latest Excel to: {target_path}")
            except Exception as exc:
                print(f"  [Excel Mirror Warning] Could not copy to {target_path}: {exc}")

    return saved_paths