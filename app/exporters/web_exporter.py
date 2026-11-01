import json
import os
import re
import shutil
import urllib.parse
from datetime import datetime
from typing import List
from app.models.tender import Tender


def _identify_source_portal(source: str, link: str, tender_no: str, department: str) -> str:
    link_l = (link or "").lower()
    t_no_l = (tender_no or "").lower()
    dept_l = (department or "").lower()
    src_l = (source or "").lower()

    if "gem.gov.in" in link_l or t_no_l.startswith("gem/") or src_l == "gem":
        return "GeM Portal"
    if "ocac.in" in link_l or "ocac" in src_l or "ocac" in dept_l:
        return "OCAC Portal"
    if "tendersodisha.gov.in" in link_l or "tendersodisha" in src_l:
        return "Odisha Tenders (NIC)"
    if "omtes" in link_l or "omtes" in src_l or "tribal education" in dept_l:
        return "OMTES Portal"
    if "osic" in link_l or "osic" in src_l or "small industries" in dept_l:
        return "OSIC Portal"
    if "stsc" in link_l or "stsc" in src_l or "sc & st" in dept_l:
        return "ST & SC Dev Portal"
    if "crut" in link_l or "urban" in src_l or "transport" in dept_l:
        return "Urban & Transport"
    if ".odisha.gov.in" in link_l:
        try:
            parsed_netloc = urllib.parse.urlparse(link).netloc
            parts = parsed_netloc.split(".")
            if len(parts) > 2 and parts[-3] not in ("www", "odisha", "tenders"):
                return f"District: {parts[-3].capitalize()}"
        except Exception:
            pass
        return "Odisha State Portal"
    return source or "Odisha State Portal"


def _extract_extra_docs(tender: Tender) -> List[str]:
    raw_add = str(getattr(tender, "additional_documents", "") or "").strip()
    raw_corr = str(getattr(tender, "corrigendum", "") or "").strip()
    primary = str(getattr(tender, "link", "") or "").strip()

    combined = f"{raw_add} {raw_corr}"
    urls = re.findall(r"https?://[^\s|,]+", combined)
    seen = set()
    extra = []
    for u in urls:
        if u != primary and u not in seen:
            seen.add(u)
            extra.append(u)
    return extra


def export_to_web(
    tenders: List[Tender],
    excel_path: str,
    web_dir: str = r"E:\TenderAutomation"
) -> List[str]:
    """
    Exports enriched Tender objects to E:\\TenderAutomation\\tenders_data.json
    and mirrors odisha_tenders.xlsx to the root directory so the standalone
    website (index.html) loads instantaneously on GitHub Pages / Vercel.
    """
    os.makedirs(web_dir, exist_ok=True)
    json_path = os.path.join(web_dir, "tenders_data.json")
    root_excel_path = os.path.join(web_dir, "odisha_tenders.xlsx")
    index_html_path = os.path.join(web_dir, "index.html")
    banner_img_path = os.path.join(web_dir, "Gemini_Generated_Image.png")

    records = []
    for t in tenders:
        t_no = str(getattr(t, "tender_no", "") or "").strip()
        link = str(getattr(t, "link", "") or "").strip()
        dept = str(getattr(t, "department", "") or "").strip()
        src = str(getattr(t, "source", "") or "").strip()

        if not link.startswith("http"):
            if t_no.upper().startswith("GEM"):
                link = f"https://bidplus.gem.gov.in/all-bids?q={t_no}"
            else:
                link = "https://tendersodisha.gov.in"

        records.append({
            "tender_no": t_no,
            "title": str(getattr(t, "title", "") or "").strip(),
            "source": src,
            "source_portal": _identify_source_portal(src, link, t_no, dept),
            "department": dept,
            "category": str(getattr(t, "category", "") or "General").strip(),
            "district": str(getattr(t, "district", "") or "Odisha").strip() or "Odisha",
            "state": str(getattr(t, "state", "Odisha") or "Odisha").strip(),
            "address": str(getattr(t, "address", "") or "").strip(),
            "quantity": str(getattr(t, "quantity", "") or "").strip(),
            "tender_value": str(getattr(t, "tender_value", "") or "").strip(),
            "budget": str(getattr(t, "budget", "") or "").strip(),
            "emd": str(getattr(t, "emd", "") or "").strip(),
            "emd_eligibility": str(getattr(t, "emd_eligibility", "") or "").strip(),
            "oem_requirement": str(getattr(t, "oem_requirement", "") or "").strip(),
            "past_experience": str(getattr(t, "past_experience", "") or "").strip(),
            "turnover_requirement": str(getattr(t, "turnover_requirement", "") or "").strip(),
            "tender_type": str(getattr(t, "tender_type", "") or "").strip(),
            "bid_type": str(getattr(t, "bid_type", "") or "").strip(),
            "published_date": str(getattr(t, "published_date", "") or "").strip(),
            "opening_date": str(getattr(t, "opening_date", "") or "").strip(),
            "closing_date": str(getattr(t, "closing_date", "") or "").strip(),
            "corrigendum": str(getattr(t, "corrigendum", "") or "").strip(),
            "summary": str(getattr(t, "summary", "") or "").strip(),
            "status": str(getattr(t, "status", "Ongoing") or "Ongoing").strip(),
            "link": link,
            "additional_documents": _extract_extra_docs(t),
        })

    payload = {
        "last_updated": datetime.now().strftime("%d %b %Y, %I:%M %p IST"),
        "total_tenders": len(records),
        "tenders": records,
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    synced_files = [json_path]

    if os.path.exists(excel_path) and os.path.abspath(excel_path) != os.path.abspath(root_excel_path):
        shutil.copy2(excel_path, root_excel_path)
    if os.path.exists(root_excel_path):
        synced_files.append(root_excel_path)
    if os.path.exists(index_html_path):
        synced_files.append(index_html_path)
    if os.path.exists(banner_img_path):
        synced_files.append(banner_img_path)

    print(f"  [Web Exporter] Generated {json_path} with {len(records)} tenders.")
    return synced_files