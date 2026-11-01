import json
import os
import time
from typing import Any, Dict, Optional

from google import genai
from google.genai import types
from openai import OpenAI


class AIDocumentExtractor:
    """
    AI-Powered Tender Document Extractor with Multi-Provider Priority Rotation:
    1. Google GenAI SDK (Gemini-3.6-flash)
    2. Groq API (openai/gpt-oss-20b / openai/gpt-oss-120b)
    3. NVIDIA NIM API (Nemotron-3.5-Lightning-30B)
    """

    def __init__(self, api_key: Optional[str] = None):
        self.gemini_api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.groq_api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.nvidia_api_key = os.environ.get("NVIDIA_API_KEY")

        # 1. Initialize Google client
        self.google_client = None
        if self.gemini_api_key:
            self.google_client = genai.Client(api_key=self.gemini_api_key)

        # 2. Initialize Groq OpenAI-compatible client
        self.groq_client = None
        if self.groq_api_key:
            self.groq_client = OpenAI(
                api_key=self.groq_api_key,
                base_url="https://api.groq.com/openai/v1"
            )

        # 3. Initialize NVIDIA OpenAI-compatible client
        self.nvidia_client = None
        if self.nvidia_api_key:
            self.nvidia_client = OpenAI(
                api_key=self.nvidia_api_key,
                base_url="https://integrate.api.nvidia.com/v1"
            )

    def extract_tender_details(self, raw_text: str, source: str = "District") -> Dict[str, str]:
        if not raw_text or not raw_text.strip():
            return {}

        prompt = f"""
Analyze the following raw tender document text from source: '{source}'.

Extract the following fields and return ONLY a valid JSON object with these exact keys:
{{
  "district": "The primary Odisha district of execution/delivery (e.g. Mayurbhanj, Sundargarh, Balasore, Khordha).",
  "address": "The full delivery / consignee address block if available",
  "quantity": "Total item quantity or scope",
  "tender_value": "Estimated Tender / Bid Value in INR (numbers only, no currency symbols)",
  "budget": "Budget or approximate cost if explicitly mentioned",
  "emd": "Earnest Money Deposit (EMD) amount in INR (numbers only, or 'Exempted')",
  "emd_eligibility": "EMD exemption details (e.g. Yes, No, Allowed for MSME/NSIC)",
  "oem_requirement": "Whether OEM authorization is required (Yes / No / Not Mentioned)",
  "past_experience": "Past experience required (e.g. '3 Years')",
  "turnover_requirement": "Average annual turnover requirement",
  "tender_type": "Type of tender (e.g. Open Tender, Limited, Quotation)",
  "published_date": "Date of publication or issue (DD-MM-YYYY)",
  "opening_date": "Date of bid opening (DD-MM-YYYY)",
  "closing_date": "Bid submission end date (DD-MM-YYYY)",
  "corrigendum": "Any corrigendum or amendment notice details",
  "summary": "A concise 2-3 sentence executive summary highlighting the equipment, service scope, and objective of the tender."
}}

--- TENDER TEXT START ---
{raw_text[:12000]}
--- TENDER TEXT END ---
"""

        system_instruction = (
            "You are an expert government tender analyst. Your task is to extract exact "
            "factual fields from the provided tender notice text. "
            "Output strictly valid JSON matching the requested keys. If a field cannot be found, use an empty string."
        )

        # -------------------------------------------------------------
        # TIER 1: Try Google Gemini (gemini-3.6-flash)
        # -------------------------------------------------------------
        if self.google_client:
            try:
                response = self.google_client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                        system_instruction=system_instruction
                    )
                )
                parsed = self._parse_json_response(response.text)
                if parsed:
                    print("  [AI SUCCESS] Extracted using Google (gemini-3.6-flash)")
                    return parsed
            except Exception as exc:
                print(f"  [Google gemini-3.6-flash Error]: {exc}")

        # -------------------------------------------------------------
        # TIER 2: Fallback to Groq (openai/gpt-oss-20b / openai/gpt-oss-120b)
        # -------------------------------------------------------------
        if self.groq_client:
            for model in ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]:
                try:
                    print(f"  [FALLBACK] Attempting extraction with Groq ({model})...")
                    response = self.groq_client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_instruction},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.1,
                        response_format={"type": "json_object"}
                    )
                    parsed = self._parse_json_response(response.choices[0].message.content)
                    if parsed:
                        print(f"  [AI SUCCESS] Extracted using Groq ({model})")
                        return parsed
                except Exception as exc:
                    print(f"  [Groq {model} Error]: {exc}")

        # -------------------------------------------------------------
        # TIER 3: Fallback to NVIDIA NIM (nemotron-3.5-lightning-30b-a3b)
        # -------------------------------------------------------------
        if self.nvidia_client:
            try:
                print("  [FALLBACK] Attempting extraction with NVIDIA NIM (nvidia/nemotron-3.5-lightning-30b-a3b)...")
                response = self.nvidia_client.chat.completions.create(
                    model="nvidia/nemotron-3.5-lightning-30b-a3b",
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                parsed = self._parse_json_response(response.choices[0].message.content)
                if parsed:
                    print("  [AI SUCCESS] Extracted using NVIDIA NIM")
                    return parsed
            except Exception as exc:
                print(f"  [NVIDIA NIM Error]: {exc}")

        print("  [CRITICAL AI ERROR] All providers and models failed.")
        return {}

    def _parse_json_response(self, text: Optional[str]) -> Dict[str, str]:
        if not text:
            return {}
        try:
            cleaned = text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            result_json = json.loads(cleaned)
            return {k: str(v).strip() if v is not None else "" for k, v in result_json.items()}
        except Exception:
            return {}