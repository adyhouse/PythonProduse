import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE = "https://www.mobilesentrix.eu"
TARGET_PATH_PREFIXES = (
    "/replacement-parts",
    "/accessories",
    "/repair-tools",
    "/devicesystem",
    "/gapp",
    "/clearance",
    "/wholesale",
)
PAGES = [
    BASE,
    f"{BASE}/replacement-parts",
    f"{BASE}/accessories",
    f"{BASE}/repair-tools",
    f"{BASE}/repair-tools/recently-added",
]
OUTPUT_JSON = Path("data/ms_categories.json")
OUTPUT_TXT = Path("data/ms_categories.txt")
OUTPUT_FILTERED = Path("data/ms_categories_filtered.txt")


def fetch(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122 Safari/537.36",
    }
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    return resp.text


def normalize_href(href: str) -> str:
    if not href:
        return ""
    parsed = urlparse(href)
    if parsed.netloc and parsed.netloc not in ("www.mobilesentrix.eu", "mobilesentrix.eu"):
        return ""  # external
    if not parsed.path:
        return ""
    # Keep path + optional query (for devicesystem filters)
    path = parsed.path
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{path}{query}"


def looks_like_category(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in TARGET_PATH_PREFIXES)


def label_from_anchor(a) -> str:
    text = a.get_text(strip=True) or ""
    text = re.sub(r"\s+", " ", text)
    return text


def main():
    categories = {}

    for url in PAGES:
        try:
            html = fetch(url)
        except Exception as e:
            print(f"WARN: cannot fetch {url}: {e}")
            continue

        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            path = normalize_href(a["href"])
            if not path:
                continue
            if not looks_like_category(path):
                continue
            label = label_from_anchor(a)
            if not label:
                # fallback to slug
                label = path.strip("/").split("/")[-1].replace("-", " ")
            if path not in categories:
                categories[path] = label

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(categories, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [f"{path} | {label}" for path, label in sorted(categories.items())]
    OUTPUT_TXT.write_text("\n".join(lines), encoding="utf-8")

    # Filtered unique by last slug (best effort draft for mapping)
    slug_map = {}
    for path, label in categories.items():
        slug = path.rstrip("/").split("/")[-1]
        if not slug:
            continue
        if slug not in slug_map:
            slug_map[slug] = (path, label)

    filtered_lines = [f"{slug} | {label} | {path}" for slug, (path, label) in sorted(slug_map.items())]
    OUTPUT_FILTERED.write_text("\n".join(filtered_lines), encoding="utf-8")

    print(f"Collected {len(categories)} category-like links")
    print(f"Saved: {OUTPUT_JSON}")
    print(f"Saved: {OUTPUT_TXT}")
    print(f"Saved: {OUTPUT_FILTERED}")


if __name__ == "__main__":
    main()
