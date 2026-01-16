# LLM Usage Log

This file records all interactions with the LLM for **Project 1: Faculty Data Cleaning**.  
Each entry includes the prompt, the response, and the tool used.

---

## Entry 1

- **Date:** 2026-01-16  
- **Tool Used:** ChatGPT (LLM)  
- **Purpose:** Generate Python code to clean faculty profile JSON data.  
- **Context:** Transformation pipeline — normalize fields, handle nulls, strip HTML, and enforce strict schema.  

### Prompt

You are a Data Transformation Assistant.
Generate Python code to clean faculty profile data stored in JSON.
File handling:
Input file: Data/faculty_profiles.json
Output file: Data/faculty_cleaned.json
Use OS-safe, project-relative paths (the script may be inside a subfolder).
Cleaning rules (apply to every record):
Normalize: name, education, biography, specialization, teaching, publications, contact, profile_url
Replace missing, empty, null, or placeholder values with:
"Not Available" for strings
[] for lists
Remove HTML tags, weird characters, and extra whitespace
Separate education and biography if mixed
Ensure teaching and publications are lists of clean strings
Merge phone, email, and address into a single contact object
Remove #, room numbers, and block identifiers from addresses
Do not infer missing data
Output schema (strict):
{
  "name": "",
  "education": "",
  "biography": "",
  "specialization": "",
  "teaching": [],
  "publications": [],
  "contact": { "phone": "", "email": "", "address": "" },
  "profile_url": ""
}
Apply to all records and write valid JSON output.
Return only the Python code.


### Response
import json
import os
import re
from html import unescape
from typing import Any, Dict, List

# ---------------- PATHS (OS-SAFE, PROJECT-RELATIVE) ---------------- #

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(BASE_DIR, "..", "Data", "faculty_profiles.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "..", "Data", "faculty_cleaned.json")

# ---------------- CONSTANTS ---------------- #

NOT_AVAILABLE = "Not Available"

PLACEHOLDER_VALUES = {
    "", None, "null", "None", "NA", "N/A", "-", "--", "—"
}

# ---------------- CLEANING UTILITIES ---------------- #

def normalize_whitespace(text: str) -> str:
    text = unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)            # remove HTML tags
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def clean_string(value: Any) -> str:
    if value in PLACEHOLDER_VALUES:
        return NOT_AVAILABLE
    if not isinstance(value, str):
        return NOT_AVAILABLE
    value = normalize_whitespace(value)
    return value if value else NOT_AVAILABLE

def clean_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    cleaned = []
    for item in value:
        if isinstance(item, str):
            item = normalize_whitespace(item)
            if item and item not in PLACEHOLDER_VALUES:
                cleaned.append(item)
    return cleaned

def clean_address(address: str) -> str:
    if address in PLACEHOLDER_VALUES:
        return NOT_AVAILABLE
    address = normalize_whitespace(address)
    address = re.sub(r"#\s*\w+", "", address)          # remove room numbers like #1105
    address = re.sub(r"\b(block|room|rm)\b.*", "", address, flags=re.I)
    address = re.sub(r"\s{2,}", " ", address)
    return address.strip() if address.strip() else NOT_AVAILABLE

def split_education_bio(education: str, biography: str) -> (str, str):
    """
    If education accidentally contains bio-like sentences, separate crudely but safely.
    No inference — just structural cleanup.
    """
    edu = clean_string(education)
    bio = clean_string(biography)

    if edu != NOT_AVAILABLE and "." in edu and bio == NOT_AVAILABLE:
        parts = edu.split(".", 1)
        edu = parts[0].strip()
        bio = parts[1].strip() if len(parts) > 1 else NOT_AVAILABLE

    return edu or NOT_AVAILABLE, bio or NOT_AVAILABLE

# ---------------- CORE TRANSFORMATION ---------------- #

def transform_record(record: Dict[str, Any]) -> Dict[str, Any]:
    name = clean_string(record.get("name"))
    education_raw = record.get("education")
    biography_raw = record.get("biography")
    specialization = clean_string(record.get("specialization"))
    teaching = clean_list(record.get("teaching"))
    publications = clean_list(record.get("publications"))
    profile_url = clean_string(record.get("profile_url"))

    education, biography = split_education_bio(
        education_raw, biography_raw
    )

    contact = {
        "phone": clean_string(record.get("phone")),
        "email": clean_string(record.get("email")),
        "address": clean_address(record.get("address"))
    }

    return {
        "name": name,
        "education": education,
        "biography": biography,
        "specialization": specialization,
        "teaching": teaching,
        "publications": publications,
        "contact": contact,
        "profile_url": profile_url
    }

# ---------------- DRIVER ---------------- #

def main():
    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    cleaned_records = []
    for record in data:
        try:
            cleaned_records.append(transform_record(record))
        except Exception:
            # Skip malformed records without crashing
            continue

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned_records, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()


---

## Entry 2

- **Date:** 2026-01-16  
- **Tool Used:** ChatGPT (LLM)  
- **Purpose:** Fix type annotation error in `split_education_bio`.  
- **Context:** Ensure valid Python typing for tuple return values.  

### Prompt

There is a Python type annotation error in the code.
The return type of split_education_bio is written incorrectly as (str, str).

Fix only this issue by replacing it with a valid tuple type annotation


### Response

from typing import Tuple

def split_education_bio(education: str, biography: str) -> Tuple[str, str]:
    """
    If education accidentally contains bio-like sentences, separate crudely but safely.
    No inference — just structural cleanup.
    """
    edu = clean_string(education)
    bio = clean_string(biography)

    if edu != NOT_AVAILABLE and "." in edu and bio == NOT_AVAILABLE:
        parts = edu.split(".", 1)
        edu = parts[0].strip()
        bio = parts[1].strip() if len(parts) > 1 else NOT_AVAILABLE

    return edu or NOT_AVAILABLE, bio or NOT_AVAILABLE


---

## Notes

- The **purpose** of these entries is **data cleaning and transformation**, not scraping.  
- Each entry logs **prompt + response** with metadata (date, tool, purpose, context).  
- Code snippets are preserved exactly as generated.  
- This log ensures reproducibility and compliance with the **LLM Policy**.

