#!/usr/bin/env python3
"""Generate a font image enum JSON for miaomiaoks.com.

This script downloads the font image references from a miaomiaoks novel
and writes a JSON file mapping image IDs to URLs, occurrence contexts, and
optional local image files.

Usage:
  python generate_miaomiaoks_font_enum.py --start-url https://www.miaomiaoks.com/read/105519/ --output miaomiaoks_font_enum.json
"""

import argparse
import json
import os
import re
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

FONT_URL_TEMPLATE = "https://www.miaomiaoks.com/asset/fonts/{id}.png"
CONTENT_LINK_RE = re.compile(r"/content/(\d+)/(\d+)\.html")


def fetch_text(url, session, timeout=20):
    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def normalize_url(base_url, href):
    if not href:
        return None
    href = href.strip()
    if href.startswith("javascript:") or href.startswith("#"):
        return None
    return urljoin(base_url, href)


def find_font_occurrences(html, base_url):
    occurrences = {}
    soup = BeautifulSoup(html, "html.parser")
    for img in soup.find_all("img", src=True):
        src = img["src"]
        if "/asset/fonts/" not in src:
            continue
        m = re.search(r"/asset/fonts/(\d+)\.png", src)
        if not m:
            continue
        font_id = m.group(1)
        url = normalize_url(base_url, src)
        context = img.parent.get_text(" ", strip=True) if img.parent else str(img)
        occurrences.setdefault(font_id, []).append({
            "url": url,
            "context": context,
        })
    return occurrences


def gather_content_urls(html, base_url, novel_id=None):
    urls = []
    seen = set()
    for match in re.finditer(r'href=["\']?([^"\'>]+)["\']?', html, re.IGNORECASE):
        raw_href = match.group(1)
        full = normalize_url(base_url, raw_href)
        if not full:
            continue
        parsed = urlparse(full)
        if parsed.netloc != urlparse(base_url).netloc:
            continue
        m = CONTENT_LINK_RE.search(parsed.path)
        if not m:
            continue
        if novel_id and m.group(1) != novel_id:
            continue
        if full not in seen:
            seen.add(full)
            urls.append(full)
    urls.sort(key=lambda u: int(CONTENT_LINK_RE.search(urlparse(u).path).group(2)))
    return urls


def build_initial_mapping(max_id=104):
    mapping = {}
    for i in range(1, max_id + 1):
        mapping[str(i)] = {
            "id": i,
            "url": FONT_URL_TEMPLATE.format(id=i),
            "character": None,
            "contexts": [],
        }
    return mapping


def download_font_images(mapping, output_dir, session):
    os.makedirs(output_dir, exist_ok=True)
    for font_id, entry in mapping.items():
        image_path = os.path.join(output_dir, f"{font_id}.png")
        if os.path.exists(image_path):
            continue
        resp = session.get(entry["url"], timeout=20)
        resp.raise_for_status()
        with open(image_path, "wb") as out_f:
            out_f.write(resp.content)
    return output_dir


def main():
    parser = argparse.ArgumentParser(description="Generate miaomiaoks font image enum JSON.")
    parser.add_argument("--start-url", required=True, help="Novel start URL, e.g. https://www.miaomiaoks.com/read/105519/")
    parser.add_argument("--output", default="miaomiaoks_font_enum.json", help="Output JSON filename")
    parser.add_argument("--max-font-id", type=int, default=104, help="Maximum font image ID to enumerate")
    parser.add_argument("--max-pages", type=int, default=30, help="Maximum number of content pages to fetch")
    parser.add_argument("--download-images", help="Optional local directory to download font PNG files")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between page requests")
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    mapping = build_initial_mapping(max_id=args.max_font_id)
    print(f"Initialized {len(mapping)} font entries.")

    html = fetch_text(args.start_url, session)
    start_occurrences = find_font_occurrences(html, args.start_url)
    for font_id, entries in start_occurrences.items():
        mapping[font_id]["contexts"].extend(entries)

    parsed = urlparse(args.start_url)
    novel_id = None
    m = re.search(r"/read/(\d+)/", parsed.path)
    if m:
        novel_id = m.group(1)

    chapter_urls = gather_content_urls(html, args.start_url, novel_id)
    if not chapter_urls and "/content/" in args.start_url:
        chapter_urls = [args.start_url]

    if not chapter_urls:
        print("No content page links found on the start URL. Only the start page will be scanned.")
    else:
        print(f"Found {len(chapter_urls)} content page links.")

    for idx, page_url in enumerate(chapter_urls[: args.max_pages], start=1):
        print(f"Fetching page {idx}/{min(len(chapter_urls), args.max_pages)}: {page_url}")
        try:
            page_html = fetch_text(page_url, session)
            occurrences = find_font_occurrences(page_html, page_url)
            for font_id, entries in occurrences.items():
                mapping[font_id]["contexts"].extend(entries)
        except Exception as exc:
            print(f"Warning: failed to fetch {page_url}: {exc}")
        time.sleep(args.delay)

    if args.download_images:
        print(f"Downloading font images into {args.download_images}")
        download_font_images(mapping, args.download_images, session)

    with open(args.output, "w", encoding="utf-8") as out_f:
        json.dump(mapping, out_f, ensure_ascii=False, indent=2)
    print(f"Saved font enum JSON to {args.output}")


if __name__ == "__main__":
    main()
