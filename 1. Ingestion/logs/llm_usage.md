# LLM Usage Log

This file records all interactions with the LLM for **Project 1: Faculty Scraper**.  
Each entry includes the prompt, the response, and the tool used.

---

## Entry 1

**Date:** 2026-01-16  
**Tool Used:** ChatGPT (LLM)  
**Purpose:** Generate complete Python scraping code for DA-IICT faculty profiles.  

### Prompt

You are a Data Engineer.
Write COMPLETE, RUNNABLE Python code using requests and BeautifulSoup to scrape all faculty profiles from the DA-IICT website.
The output must be clean JSON suitable for ingestion.
Do not use browser automation.
Do not use shell commands.
The code must run as-is.

1. Faculty category URLs
Scrape all the following listing pages.
Faculty type must be assigned strictly from the listing URL, never inferred from profile pages.
https://www.daiict.ac.in/faculty
faculty_type = core
https://www.daiict.ac.in/adjunct-faculty
faculty_type = adjunct
https://www.daiict.ac.in/adjunct-faculty-international
faculty_type = international
https://www.daiict.ac.in/distinguished-professor
faculty_type = distinguished
https://www.daiict.ac.in/professor-practice
faculty_type = practice

2.Global deduplication
Each faculty member must be scraped exactly once.
Use profile_url as the unique key.
Maintain a global set of visited profile URLs.
If a profile URL is already processed, skip it.
Expected total unique profiles is approximately 109 across all listing pages combined.

3.Scraping listing pages
On each listing page, locate faculty cards at:
div.facultyInformation > ul > li
Each <li> corresponds to exactly one faculty member.
From each <li>, extract ONLY:
name from h3 a
profile_url from h3 a[href]
faculty_type from the listing URL
source_listing_url as the current listing page URL
Do NOT extract specialization, biography, publications, or teaching from listing pages.

4.Scraping profile pages (authoritative source)
Each profile page is a Drupal faculty node.
Extract fields using the exact rules below.
Do not infer data.
Do not mix sections.
4.1 Name
Selector:
.field--name-field-faculty-names
4.2 Education
Selector:
.field--name-field-faculty-name
4.3 Phone
Selector:
.field--name-field-contact-no
If missing, store empty string.
4.4 Email
Selector:
.field--name-field-email .field__item
4.5 Address
Selector:
.field--name-field-address
4.6 Biography
Selector:
.field--name-field-biography
If missing, store null.
Do not include headings or “KNOW MORE”.
4.7 Specialization
On the profile page, specialization is structured as follows:
An <h2> element with text exactly "Specialization"
This <h2> is wrapped inside a <div class="specializationIcon">
The specialization content is in the NEXT sibling <div class="work-exp">
Extraction rule:
Find <h2> whose text is exactly "Specialization"
Get its parent div with class specializationIcon
From that parent, select the next sibling div with class work-exp
Extract and normalize all text inside this div
Ignore nested or malformed <p> tags
If this structure does not exist, store specialization as an empty string.
Do NOT infer specialization from biography, publications, or teaching.
4.8 Publications
Publications must be extracted ONLY from the "Publications" section.
Extraction rule:
Find <h2> with text exactly "Publications"
From that <h2>, move forward in the DOM until the first <ul class="bulletText">
Extract text from its direct <li> children only
Stop extraction at the end of that <ul>
Do not collect text from any other <ul>.
If this <ul> does not exist, store an empty list.
4.9 Teaching
Teaching is a Drupal field that may contain plain text nodes, <br> breaks, or malformed markup.
Selector:
.field--name-field-teaching
Extraction rule:
Extract teaching entries from the text nodes inside this element.
Split content using line breaks or stripped text segments.
Each non-empty text segment is one teaching item.
Do NOT look for <li> tags.
Do NOT call .get_text() on individual items.
If the field is missing or empty, store an empty list.

5. Output
Write all data into a single file named:
faculty_profiles.json
Each faculty record must follow this schema exactly:
{
"name": "",
"faculty_type": "",
"education": "",
"phone": "",
"email": "",
"address": "",
"specialization": "",
"profile_url": "",
"biography": null,
"publications": [],
"teaching": [],
"source_listing_url": "",
"scraped_at": "ISO-8601 timestamp"
}

6. Engineering constraints (mandatory)
Faculty type must never be inferred from profile pages.
Profile page data overrides listing page data.
Publications must never contain specialization or teaching text.
Teaching must never be extracted from lists near publications.
Missing fields must not break the scraper.
Use only requests and BeautifulSoup.
Error handling and robustness
The code must handle the following gracefully without crashing:
If a listing page is unavailable or returns non-200 status, log the error and exit cleanly.
If a profile page fails to load, log the profile_url and continue scraping others.
If any field selector is missing, return empty string, null, or empty list as appropriate.
All exceptions must be caught and logged with URL context.
Modularity requirement
The code must be modular and readable.
At minimum, define functions for:
fetch_html(url)
parse_listing_page(html, listing_url, faculty_type)
parse_profile_page(html, profile_url, faculty_type, source_listing_url)
validate_record(record)
write_output(records, filename)
No scraping logic should exist outside these functions.

Generate the complete Python scraping code that satisfies ALL requirements above.


### Response
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
---

## Notes

- All scraping logic was generated by the LLM in one prompt.  
- The code adheres to modularity requirements (`fetch_html`, `parse_listing_page`, `parse_profile_page`, `validate_record`, `write_output`).  
- Error handling, deduplication, and JSON output schema are included.  
- This log ensures compliance with the **LLM Policy** stated in the project document.
