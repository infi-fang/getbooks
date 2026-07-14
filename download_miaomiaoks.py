#!/usr/bin/env python3
"""
Dedicated downloader for miaomiaoks.com novel pages.

Usage:
  python download_miaomiaoks.py --url "https://www.miaomiaoks.com/read/105519/" --output "mybook.txt"
  python download_miaomiaoks.py --url "https://www.miaomiaoks.com/content/105519/1.html" --output "mybook.txt"

This script collects all volume pages under a target novel, extracts the main text from each
volume, and writes a single TXT file with clear volume headings.
"""

import argparse
import re
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def get_soup(url, session, timeout=20):
    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def extract_text_from_soup(soup):
    for cls in ["content", "chapter-content", "read-content", "book-content"]:
        el = soup.find("div", class_=cls)
        if el:
            text = el.get_text("\n", strip=True)
            if len(text) > 50:
                return clean_text(text)

    el = soup.find("article") or soup.body
    if el:
        text = el.get_text("\n", strip=True)
        return clean_text(text)

    return ""


def clean_text(text):
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join([line for line in lines if line])


def normalize_url(base_url, href):
    if not href:
        return None
    href = href.strip()
    if href.startswith("javascript:") or href.startswith("#"):
        return None
    return urljoin(base_url, href)


def get_miaomiaoks_novel_id(url):
    parsed = urlparse(url)
    if parsed.netloc not in ("www.miaomiaoks.com", "miaomiaoks.com"):
        return None
    m = re.match(r"^/read/(\d+)/?$", parsed.path)
    if m:
        return m.group(1)
    m = re.match(r"^/content/(\d+)/", parsed.path)
    if m:
        return m.group(1)
    return None


def find_volume_links(soup, base_url, novel_id):
    if not novel_id:
        return []

    links = []
    seen = set()
    for a in soup.find_all("a", href=True):
        full = normalize_url(base_url, a["href"])
        if not full:
            continue
        parsed = urlparse(full)
        if parsed.netloc != urlparse(base_url).netloc:
            continue

        match = re.match(rf"^/content/{re.escape(novel_id)}/(\d+)\.html$", parsed.path)
        if match:
            num = int(match.group(1))
            title = a.get_text(strip=True) or f"分卷阅读{num}"
            if full not in seen:
                seen.add(full)
                links.append((num, title, full))

    links.sort(key=lambda item: item[0])
    return [(title, url) for _, title, url in links]


def build_output_title(soup, url):
    title = None
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    if title:
        title = title.replace("_喵喵看书", "").strip()
    if not title:
        title = url
    return title


def download_miaomiaoks(url, output_path, delay=1.0, max_volumes=0):
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    print("Fetching start URL:", url)
    soup = get_soup(url, session)
    novel_id = get_miaomiaoks_novel_id(url)
    if not novel_id:
        raise ValueError("URL is not a supported miaomiaoks.com novel URL.")

    volume_links = find_volume_links(soup, url, novel_id)
    if not volume_links:
        if "/content/" in url:
            volume_links = [("当前分卷", url)]
        else:
            raise RuntimeError("未能找到任何分卷链接，请检查 URL 是否正确。")

    if max_volumes and max_volumes > 0:
        volume_links = volume_links[:max_volumes]

    novel_title = build_output_title(soup, url)
    print(f"Found {len(volume_links)} volume pages for '{novel_title}'.")

    with open(output_path, "w", encoding="utf-8") as out_file:
        out_file.write(novel_title + "\n")
        out_file.write("=" * len(novel_title) + "\n\n")

        for idx, (label, link) in enumerate(volume_links, start=1):
            print(f"[{idx}/{len(volume_links)}] Downloading {label}: {link}")
            volume_soup = get_soup(link, session)
            text = extract_text_from_soup(volume_soup)
            if not text:
                print("Warning: 未提取到内容，跳过", link)
                continue

            section_title = f"{label}"
            out_file.write(section_title + "\n")
            out_file.write("-" * len(section_title) + "\n\n")
            out_file.write(text + "\n\n")
            time.sleep(delay)

    print("Download complete ->", output_path)


def main():
    parser = argparse.ArgumentParser(description="Download novel text from miaomiaoks.com")
    parser.add_argument("--url", required=True, help="Target novel URL, e.g. https://www.miaomiaoks.com/read/105519/")
    parser.add_argument("--output", default="miaomiaoks_book.txt", help="Output TXT filename")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay in seconds between requests")
    parser.add_argument("--max-volumes", type=int, default=0, help="Maximum number of volume pages to download (0 = all)")
    args = parser.parse_args()

    download_miaomiaoks(args.url, args.output, delay=args.delay, max_volumes=args.max_volumes)


if __name__ == "__main__":
    main()
