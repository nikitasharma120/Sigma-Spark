import requests
import json
import logging
from bs4 import BeautifulSoup, NavigableString
from datetime import datetime
from typing import List, Dict, Set, Optional

# ---------------- CONFIG ---------------- #

OUTPUT_FILE = "faculty_profiles.json"
TIMEOUT = 20

LISTING_PAGES = [
    ("https://www.daiict.ac.in/faculty", "core"),
    ("https://www.daiict.ac.in/adjunct-faculty", "adjunct"),
    ("https://www.daiict.ac.in/adjunct-faculty-international", "international"),
    ("https://www.daiict.ac.in/distinguished-professor", "distinguished"),
    ("https://www.daiict.ac.in/professor-practice", "practice"),
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ---------------- UTILITIES ---------------- #

def fetch_html(url: str) -> Optional[str]:
    try:
        resp = requests.get(url, timeout=TIMEOUT)
        if resp.status_code != 200:
            logging.error(f"Non-200 response [{resp.status_code}] for URL: {url}")
            return None
        return resp.text
    except Exception as e:
        logging.exception(f"Failed to fetch URL: {url}")
        return None

# ---------------- LISTING PARSER ---------------- #

def parse_listing_page(html: str, listing_url: str, faculty_type: str) -> List[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    records = []

    try:
        cards = soup.select("div.facultyInformation > ul > li")
        for li in cards:
            a_tag = li.select_one("h3 a")
            if not a_tag or not a_tag.get("href"):
                continue

            records.append({
                "name": a_tag.get_text(strip=True),
                "profile_url": a_tag["href"].strip(),
                "faculty_type": faculty_type,
                "source_listing_url": listing_url
            })
    except Exception:
        logging.exception(f"Error parsing listing page: {listing_url}")

    return records

# ---------------- PROFILE PARSER ---------------- #

def _safe_text(soup: BeautifulSoup, selector: str) -> str:
    el = soup.select_one(selector)
    return el.get_text(strip=True) if el else ""

def parse_profile_page(
    html: str,
    profile_url: str,
    faculty_type: str,
    source_listing_url: str
) -> Optional[Dict]:

    soup = BeautifulSoup(html, "html.parser")

    try:
        # ---------- BASIC FIELDS ----------
        name = _safe_text(soup, ".field--name-field-faculty-names")
        education = _safe_text(soup, ".field--name-field-faculty-name")
        phone = _safe_text(soup, ".field--name-field-contact-no")
        email = _safe_text(soup, ".field--name-field-email .field__item")
        address = _safe_text(soup, ".field--name-field-address")

        bio_el = soup.select_one(".field--name-field-biography")
        biography = bio_el.get_text(strip=True) if bio_el else None

        # ---------- SPECIALIZATION ----------
        specialization = ""
        for h2 in soup.find_all("h2"):
            if h2.get_text(strip=True) == "Specialization":
                parent = h2.find_parent("div", class_="specializationIcon")
                if parent:
                    next_div = parent.find_next_sibling("div", class_="work-exp")
                    if next_div:
                        specialization = " ".join(next_div.stripped_strings)
                break

        # ---------- PUBLICATIONS ----------
        publications = []
        for h2 in soup.find_all("h2"):
            if h2.get_text(strip=True) == "Publications":
                ul = h2.find_next("ul", class_="bulletText")
                if ul:
                    for li in ul.find_all("li", recursive=False):
                        text = li.get_text(strip=True)
                        if text:
                            publications.append(text)
                break

        # ---------- TEACHING ----------
        teaching = []
        teaching_el = soup.select_one(".field--name-field-teaching")
        if teaching_el:
            segments = []
            for node in teaching_el.descendants:
                if isinstance(node, NavigableString):
                    text = node.strip()
                    if text:
                        segments.append(text)
            teaching = segments

        record = {
            "name": name,
            "faculty_type": faculty_type,
            "education": education,
            "phone": phone,
            "email": email,
            "address": address,
            "specialization": specialization,
            "profile_url": profile_url,
            "biography": biography,
            "publications": publications,
            "teaching": teaching,
            "source_listing_url": source_listing_url,
            "scraped_at": datetime.utcnow().isoformat()
        }

        return record

    except Exception:
        logging.exception(f"Error parsing profile page: {profile_url}")
        return None

# ---------------- VALIDATION ---------------- #

def validate_record(record: Dict) -> bool:
    required_keys = [
        "name", "faculty_type", "education", "phone", "email", "address",
        "specialization", "profile_url", "biography", "publications",
        "teaching", "source_listing_url", "scraped_at"
    ]
    for key in required_keys:
        if key not in record:
            return False
    return True

# ---------------- OUTPUT ---------------- #

def write_output(records: List[Dict], filename: str):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    logging.info(f"Wrote {len(records)} records to {filename}")

# ---------------- MAIN DRIVER ---------------- #

def main():
    visited_profiles: Set[str] = set()
    final_records: List[Dict] = []

    for listing_url, faculty_type in LISTING_PAGES:
        logging.info(f"Scraping listing: {listing_url}")
        html = fetch_html(listing_url)
        if not html:
            logging.error("Listing page failed — exiting cleanly.")
            return

        listing_records = parse_listing_page(html, listing_url, faculty_type)

        for entry in listing_records:
            profile_url = entry["profile_url"]
            if profile_url in visited_profiles:
                continue

            visited_profiles.add(profile_url)
            logging.info(f"Scraping profile: {profile_url}")

            profile_html = fetch_html(profile_url)
            if not profile_html:
                logging.error(f"Skipping failed profile: {profile_url}")
                continue

            record = parse_profile_page(
                profile_html,
                profile_url,
                entry["faculty_type"],
                entry["source_listing_url"]
            )

            if record and validate_record(record):
                final_records.append(record)
            else:
                logging.error(f"Invalid record skipped: {profile_url}")

    write_output(final_records, OUTPUT_FILE)

# ---------------- ENTRY POINT ---------------- #

if __name__ == "__main__":
    main()
