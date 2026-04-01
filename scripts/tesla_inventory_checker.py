"""
Tesla Canada Inventory Checker
Checks for Model Y Grey AWD (cheapest) near Calgary T3L 0A4 within 300km.
Logs results and prints new listings found since last run.

Requirements:
    pip install curl_cffi
"""

import json
import os
import sys
import time
import urllib.parse
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
POSTAL_CODE   = "T3L0M4"       # Calgary NW (no space)
RADIUS_KM     = 300
MARKET        = "CA"
REGION        = "AB"
MODEL         = "my"           # Model Y
CONDITION     = "new"
MAX_RESULTS   = 50

# Tesla grey paint codes. Set to None to see all colours.
# PMNG = Midnight Silver Metallic  |  GREY = Stealth Grey
GREY_PAINTS   = {"PMNG", "GREY"}

# AWD trim codes (cheapest AWD = Long Range AWD = LRAWD)
AWD_TRIMS     = {"LRAWD", "PAWD"}

LOG_FILE      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tesla_checker_log.json")
SEEN_FILE     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tesla_seen_vins.json")

SEED_URL      = "https://www.tesla.com/en_CA/inventory/new/my"
API_URL       = "https://www.tesla.com/inventory/api/v4/inventory-results"
# ─────────────────────────────────────────────────────────────────────────────


def build_query_url(offset: int = 0, count: int = MAX_RESULTS) -> str:
    query = {
        "query": {
            "model": MODEL,
            "condition": CONDITION,
            "options": {},
            "arrangeby": "Price",
            "order": "asc",
            "market": MARKET,
            "language": "en",
            "super_region": "north america",
            "zip": POSTAL_CODE,
            "range": RADIUS_KM,
            "region": REGION,
        },
        "offset": offset,
        "count": count,
        "outsideOffset": 0,
        "outsideSearch": False,
    }
    encoded = urllib.parse.quote(json.dumps(query, separators=(",", ":")))
    return f"{API_URL}?query={encoded}"


def fetch_inventory() -> list[dict]:
    try:
        from curl_cffi import requests as cffi_requests
    except ImportError:
        print("[ERROR] curl_cffi not installed.")
        print("  Run: pip install curl_cffi")
        sys.exit(1)

    session = cffi_requests.Session(impersonate="chrome124")
    headers_base = {
        "Accept-Language": "en-CA,en;q=0.9",
        "Referer": SEED_URL,
    }

    # Step 1: Seed session with the inventory page to acquire cookies
    print("  Seeding session...")
    try:
        seed = session.get(
            SEED_URL + "?arrangeby=plh&zip=" + POSTAL_CODE + "&range=" + str(RADIUS_KM),
            headers={"Accept": "text/html,application/xhtml+xml", **headers_base},
            timeout=15,
        )
        print(f"  Seed page: {seed.status_code}")
        time.sleep(2)
    except Exception as e:
        print(f"  Seed warning: {e}")

    # Step 2: Query inventory API with session cookies
    api_url = build_query_url()
    for attempt in range(3):
        resp = session.get(
            api_url,
            headers={"Accept": "application/json", **headers_base},
            timeout=15,
        )
        print(f"  API status: {resp.status_code} (attempt {attempt + 1})")

        if resp.status_code == 200:
            return resp.json().get("results", [])

        if resp.status_code in (429, 503):
            wait = 10 * (attempt + 1)
            print(f"  Rate limited — waiting {wait}s...")
            time.sleep(wait)
            continue

        if resp.status_code == 403:
            print("  403 Forbidden — Tesla is blocking this IP right now.")
            print("  This usually clears after a few hours. Will retry tomorrow.")
            return []

        resp.raise_for_status()

    print("[ERROR] All retry attempts failed.")
    return []


def is_grey(car: dict) -> bool:
    if GREY_PAINTS is None:
        return True
    paint = car.get("PAINT", [])
    if isinstance(paint, str):
        paint = [paint]
    return bool(set(paint) & GREY_PAINTS)


def is_awd(car: dict) -> bool:
    trim = car.get("TRIM", [])
    if isinstance(trim, str):
        trim = [trim]
    return bool(set(trim) & AWD_TRIMS)


def format_car(car: dict) -> dict:
    price = car.get("InventoryPrice") or car.get("TotalPrice") or car.get("Price")
    vin   = car.get("VIN", "N/A")
    city  = car.get("City", "")
    prov  = car.get("StateProvince", "")
    dist  = car.get("Distance", "?")
    trim  = car.get("TRIM", [])
    paint = car.get("PAINT", [])
    year  = car.get("Year", "")
    url   = f"https://www.tesla.com/en_CA/my/{vin}" if vin != "N/A" else ""

    return {
        "vin":      vin,
        "year":     year,
        "trim":     trim,
        "paint":    paint,
        "price":    price,
        "city":     f"{city}, {prov}".strip(", "),
        "distance": dist,
        "url":      url,
        "seen_at":  datetime.now().isoformat(),
    }


def load_json(path: str):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json(path: str, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def main():
    print(f"\n{'='*60}")
    print(f"Tesla Model Y Grey AWD Checker")
    print(f"Checked at: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Location:   {POSTAL_CODE}, within {RADIUS_KM}km")
    print(f"{'='*60}\n")

    all_cars = fetch_inventory()
    print(f"\nTotal results from Tesla API: {len(all_cars)}")

    # Filter grey + AWD
    matched = [c for c in all_cars if is_grey(c) and is_awd(c)]
    print(f"Matching (grey + AWD):         {len(matched)}\n")

    seen_vins: dict = load_json(SEEN_FILE) or {}
    new_found = [format_car(c) for c in matched if c.get("VIN") not in seen_vins]

    # Print results
    if not matched:
        print("No matching inventory found at this time.\n")
    else:
        print(f"{'─'*60}")
        for car in matched:
            e    = format_car(car)
            flag = " *** NEW ***" if e["vin"] not in seen_vins else ""
            price_str = f"${e['price']:,}" if isinstance(e['price'], (int, float)) else str(e['price'])
            print(
                f"  {e['year']} Model Y | "
                f"Trim: {e['trim']} | "
                f"Paint: {e['paint']} | "
                f"{price_str} | "
                f"{e['city']} ~{e['distance']}km"
                f"{flag}"
            )
            print(f"  VIN: {e['vin']}")
            print(f"  Link: {e['url']}\n")

    if new_found:
        print(f"\n{'*'*60}")
        print(f"  {len(new_found)} NEW listing(s) since last check!")
        print(f"{'*'*60}\n")
    else:
        print("No new listings since last check.\n")

    # Persist seen VINs
    all_seen = {**seen_vins, **{format_car(c)["vin"]: format_car(c) for c in matched if c.get("VIN", "N/A") != "N/A"}}
    save_json(SEEN_FILE, all_seen)

    # Append to run log
    log = load_json(LOG_FILE) if isinstance(load_json(LOG_FILE), list) else []
    log.append({
        "checked_at":    datetime.now().isoformat(),
        "total_api":     len(all_cars),
        "matched":       len(matched),
        "new_listings":  len(new_found),
        "cars":          [format_car(c) for c in matched],
    })
    save_json(LOG_FILE, log)
    print(f"Log saved -> {LOG_FILE}")


if __name__ == "__main__":
    main()
