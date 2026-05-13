import json
import re
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from pydantic import BaseModel, ValidationError

# Data model for the job listing
class JobListing(BaseModel):
    source_id: str
    job_title: str
    company: str
    description: str

# Clean and extract text from HTML content
def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()

# Extract content from meta tags based on name or property attributes
def _extract_meta_content(soup: BeautifulSoup, *, name: str | None = None, property_name: str | None = None) -> str | None:
    attrs: dict[str, str] = {}
    if name is not None:
        attrs["name"] = name
    if property_name is not None:
        attrs["property"] = property_name

    element = soup.find("meta", attrs=attrs)
    if not element:
        return None
    content = element.get("content")
    if not content:
        return None
    return str(content)

# Extract text from an element based on a selector
def _extract_text(soup: BeautifulSoup, selector: dict[str, str]) -> str | None:
    element = soup.find(attrs=selector)
    if not element:
        return None
    text = element.get_text(separator=" ", strip=True)
    if not text:
        return None
    return _normalize_text(text)

# Extract the source ID from the URL in the meta tag
def _extract_source_id(soup: BeautifulSoup) -> str | None:
    url = _extract_meta_content(soup, property_name="og:url")
    if not url:
        return None

    path = urlparse(url).path.rstrip("/")
    if not path:
        return None

    return path.split("/")[-1]

# Extract job listing details from HTML content and return a JobListing object
def _extract_job_listing(html_content: str) -> JobListing | None:
    soup = BeautifulSoup(html_content, "html.parser")

    source_id = _extract_source_id(soup)
    job_title = _extract_text(soup, {"data-automation": "job-detail-title"})
    company = _extract_text(soup, {"data-automation": "advertiser-name"})
    description_container = soup.find(attrs={"data-automation": "jobAdDetails"})
    description = None
    if description_container:
        description = _normalize_text(description_container.get_text(separator=" ", strip=True))

    required_fields = {
        "source_id": source_id,
        "job_title": job_title,
        "company": company,
        "description": description,
    }

    for field_name, field_value in required_fields.items():
        if not field_value:
            return None

    try:
        return JobListing(**required_fields)
    except ValidationError:
        return None

# Process all HTML files
def process_all_html(input_dir, output_dir):
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    total = 0
    processed = 0
    skipped = 0

    print("🥈 Silver:...")

    if not input_path.exists():
        print(f"⚠️ Input directory not found: {input_dir}")
        print("\n📊 Silver Summary:")
        print(f"Total: {total} | Processed: {processed} | Skipped: {skipped}")
        return {"total": total, "processed": processed, "skipped": skipped}

    html_files = sorted(input_path.glob("*.html"))
    if not html_files:
        print(f"⚠️ No .html files found in: {input_dir}")
        print("\n📊 Silver Summary:")
        print(f"Total: {total} | Processed: {processed} | Skipped: {skipped}")
        return {"total": total, "processed": processed, "skipped": skipped}

    for html_file in html_files:
        total += 1
        output_file = output_path / f"{html_file.stem}.json"

        try:
            html_content = html_file.read_text(encoding="utf-8")
            job_listing = _extract_job_listing(html_content)

            if not job_listing:
                print(f"⚠️ Skipped: {html_file.name}")
                skipped += 1
                continue

            with open(output_file, "w", encoding="utf-8") as file_handle:
                json.dump(job_listing.model_dump(), file_handle, ensure_ascii=False, indent=2)

            print(f"✅ Processed: {html_file.name}")
            processed += 1
        except Exception as exc:
            print(f"⚠️ Error processing {html_file.name}: {exc}")
            skipped += 1

    print("\n📊 Silver Summary:")
    print(f"Total: {total} | Processed: {processed} | Skipped: {skipped}")

    return {"total": total, "processed": processed, "skipped": skipped}


if __name__ == "__main__":
    process_all_html("data/1_bronze", "data/2_silver")