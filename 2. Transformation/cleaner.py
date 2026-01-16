import json
import os
import re
from typing import Any, Dict, List

# -------------------------------------------------------------------
# Path handling (OS-safe, project-relative)
# -------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_PATH = os.path.join(BASE_DIR, "..", "Data", "faculty_profiles.json")
OUTPUT_PATH = os.path.join(BASE_DIR, "..", "Data", "faculty_cleaned.json")

# -------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------
NA_STRING = "Not Available"

# -------------------------------------------------------------------
# Utility cleaning functions
# -------------------------------------------------------------------
def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def clean_string(value: Any) -> str:
    if not value or not isinstance(value, str):
        return NA_STRING

    cleaned = strip_html(value)
    cleaned = normalize_whitespace(cleaned)

    if cleaned in {"", "null", "None", "-", "--"}:
        return NA_STRING

    return cleaned


def clean_address(address: Any) -> str:
    if not address or not isinstance(address, str):
        return NA_STRING

    # Remove ONLY '#' symbols
    address = address.replace("#", "")
    address = strip_html(address)
    address = normalize_whitespace(address)

    return address if address else NA_STRING


def clean_list(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []

    cleaned_items = []
    for item in values:
        if isinstance(item, str):
            text = normalize_whitespace(strip_html(item))
            if text:
                cleaned_items.append(text)

    return cleaned_items


def separate_education_and_biography(education: str, biography: str) -> tuple[str, str]:
    """
    If education text is polluted with biography-like sentences,
    split conservatively without inferring new content.
    """
    if education == NA_STRING:
        return NA_STRING, biography

    if biography != NA_STRING:
        return education, biography

    # Heuristic: If education contains long paragraphs, split at first full stop
    if education.count(".") >= 2:
        parts = education.split(".", 1)
        edu = normalize_whitespace(parts[0])
        bio = normalize_whitespace(parts[1])

        return edu or NA_STRING, bio or NA_STRING

    return education, biography


# -------------------------------------------------------------------
# Record transformation
# -------------------------------------------------------------------
def transform_record(record: Dict[str, Any]) -> Dict[str, Any]:
    name = clean_string(record.get("name"))
    education_raw = clean_string(record.get("education"))
    biography_raw = clean_string(record.get("biography"))
    specialization = clean_string(record.get("specialization"))
    profile_url = clean_string(record.get("profile_url"))

    education, biography = separate_education_and_biography(
        education_raw,
        biography_raw
    )

    teaching = clean_list(record.get("teaching"))
    publications = clean_list(record.get("publications"))

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


# -------------------------------------------------------------------
# Main execution
# -------------------------------------------------------------------
def main():
    if not os.path.exists(INPUT_PATH):
        raise FileNotFoundError(f"Input file not found: {INPUT_PATH}")

    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        raw_records = json.load(f)

    cleaned_records = []
    for record in raw_records:
        try:
            cleaned_records.append(transform_record(record))
        except Exception:
            # Skip only the broken record, never crash the pipeline
            continue

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(cleaned_records, f, indent=2, ensure_ascii=False)

    print(f"Cleaned {len(cleaned_records)} records → {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
