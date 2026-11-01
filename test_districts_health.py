import json
import requests
from bs4 import BeautifulSoup
import os

def check_district_health():
    print("\n======================================")
    print("   DISTRICT PORTALS HEALTH CHECK")
    print("======================================")

    config_path = "config/websites.json"
    if not os.path.exists(config_path):
        print(f"[ERROR] Config file not found at {config_path}")
        return

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            sites = data.get("odisha_districts", [])
    except Exception as e:
        print(f"[ERROR] Could not read {config_path}: {e}")
        return

    print(f"Total district sites configured: {len(sites)}\n")
    print(f"{'District Name':<15} | {'Status':<10} | {'HTTP Code':<10} | {'Tenders Found'}")
    print("-" * 60)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    working_count = 0
    failed_count = 0

    for site in sites:
        name = site.get("name", "Unknown")
        url = site.get("url", "")
        
        if not url:
            print(f"{name:<15} | {'INVALID URL':<10} | {'N/A':<10} | 0")
            failed_count += 1
            continue

        # Ensure HTTPS protocol
        if url.startswith("http://"):
            url = url.replace("http://", "https://", 1)
        elif not url.startswith("https://"):
            url = "https://" + url

        try:
            response = requests.get(url, headers=headers, timeout=15, verify=True)
            http_code = response.status_code

            if http_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                rows = soup.find_all('tr')
                # Count rows that look like data rows (at least 3 columns)
                tender_rows = [r for r in rows if len(r.find_all('td')) >= 3]
                
                status = "WORKING"
                working_count += 1
                print(f"{name:<15} | {status:<10} | {http_code:<10} | {len(tender_rows)} rows found")
            else:
                failed_count += 1
                print(f"{name:<15} | {'ERROR':<10} | {http_code:<10} | 0 rows")

        except requests.exceptions.RequestException as e:
            failed_count += 1
            print(f"{name:<15} | {'DOWN':<10} | {'TIMEOUT':<10} | 0 rows")

    print("-" * 60)
    print(f"Health Check Summary: {working_count} Working | {failed_count} Down/Unreachable")

if __name__ == "__main__":
    check_district_health()