"""
Run this script locally to pre-scrape the SHL catalog and generate shl_catalog.json.
The catalog is then committed alongside the app, so Render doesn't need to scrape at runtime.

Usage:
    python scrape.py
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "https://www.shl.com/solutions/products/product-catalog/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

TEST_TYPE_ICONS = {
    "A": "Ability/Cognitive",
    "P": "Personality",
    "B": "Behavioral",
    "S": "Simulation/Skills",
    "K": "Knowledge",
    "M": "Motivational",
    "360": "360 Feedback",
}


def fetch_page(start: int) -> str:
    params = {
        "start": start,
        "type": 1,
        "action_doFilteringForm": "Search",
        "f": 1,
    }
    resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.text


def parse_catalog_page(html: str) -> list:
    """Parse assessments from a catalog page."""
    soup = BeautifulSoup(html, "html.parser")
    items = []

    # SHL uses a table with rows that have data-href
    table = soup.find("table")
    if not table:
        return []

    tbody = table.find("tbody")
    if not tbody:
        return []

    rows = tbody.find_all("tr")
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        # Cell 0: name + link
        link_tag = cells[0].find("a")
        if not link_tag:
            continue
        name = link_tag.get_text(strip=True)
        href = link_tag.get("href", "")
        if href and not href.startswith("http"):
            href = "https://www.shl.com" + href

        # Cell 1: Remote Testing (checkmark = yes)
        remote = bool(cells[1].find("span", {"aria-label": re.compile(r"yes|check", re.I)}) or
                      "\u2714" in cells[1].get_text() or
                      "yes" in cells[1].get_text().lower())

        # Cell 2: Adaptive/IRT
        adaptive = bool(cells[2].find("span", {"aria-label": re.compile(r"yes|check", re.I)}) or
                        "\u2714" in cells[2].get_text() or
                        "yes" in cells[2].get_text().lower())

        # Cell 3: Test type letter(s)
        type_spans = cells[3].find_all("span")
        test_types = []
        for span in type_spans:
            t = span.get("title", span.get_text(strip=True)).strip()
            if t:
                test_types.append(t)
        test_type = ",".join(test_types) if test_types else "A"

        if name and href:
            items.append({
                "name": name,
                "url": href,
                "remote_testing": remote,
                "adaptive": adaptive,
                "test_type": test_type,
                "description": "",
            })
    return items


def scrape_all() -> list:
    all_items = []
    start = 0

    while True:
        logger.info(f"Fetching page start={start}...")
        try:
            html = fetch_page(start)
            items = parse_catalog_page(html)
            if not items:
                logger.info(f"No items at start={start}. Done.")
                break
            all_items.extend(items)
            logger.info(f"  Got {len(items)} items (total={len(all_items)})")

            # Check if next page exists
            soup = BeautifulSoup(html, "html.parser")
            next_btn = soup.find("a", string=re.compile(r"Next", re.I))
            pagination = soup.find_all("li", class_=re.compile(r"pager|next"))
            has_next = next_btn or any(
                "disabled" not in (li.get("class") or []) and "next" in str(li).lower()
                for li in pagination
            )
            if not has_next or len(items) < 10:
                break

            start += 12
            time.sleep(1)
        except Exception as e:
            logger.error(f"Error at start={start}: {e}")
            break

    return all_items


def enrich_with_details(items: list, max_items: int = None) -> list:
    """Optionally fetch individual product pages for descriptions."""
    enriched = []
    for i, item in enumerate(items[:max_items]):
        try:
            resp = requests.get(item["url"], headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            # Try to find description
            desc_div = (soup.find("div", class_=re.compile(r"description|content|product-detail")) or
                        soup.find("p"))
            if desc_div:
                item["description"] = desc_div.get_text(strip=True)[:400]
            enriched.append(item)
            if i % 10 == 0:
                logger.info(f"  Enriched {i+1}/{len(items)}")
            time.sleep(0.5)
        except Exception as e:
            logger.warning(f"Could not enrich {item['name']}: {e}")
            enriched.append(item)
    return enriched


if __name__ == "__main__":
    print("Scraping SHL Individual Test Solutions catalog...")
    items = scrape_all()
    print(f"Total items scraped: {len(items)}")

    if items:
        with open("shl_catalog.json", "w") as f:
            json.dump(items, f, indent=2)
        print("Saved to shl_catalog.json")
    else:
        print("No items scraped. The site may require JavaScript rendering.")
        print("The bundled catalog in catalog.py will be used as fallback.")
