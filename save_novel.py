#!/usr/bin/env python3
"""
Novel downloader (heuristic scraper)

Usage:
  python save_novel.py --url <novel_or_label_url> --output mybook.txt

Notes and warnings:
- Only use this script for content you have the right to download.
- Respect robots.txt and site terms of service.
- The target site may block automated clients; this script uses polite delays.
"""
import argparse
import time
import sys
from urllib.parse import urljoin, urlparse

import requests
from requests import exceptions as req_exceptions
try:
    import cloudscraper
except Exception:
    cloudscraper = None
from bs4 import BeautifulSoup

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def get_soup(url, session, timeout=15):
    try:
        resp = session.get(url, timeout=timeout)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except req_exceptions.HTTPError as e:
        # If site returns 403, try cloudscraper (Cloudflare/anti-bot) if available
        status = getattr(e.response, 'status_code', None)
        if status == 403 and cloudscraper is not None:
            try:
                scraper = cloudscraper.create_scraper()
                resp = scraper.get(url, timeout=timeout)
                resp.raise_for_status()
                return BeautifulSoup(resp.text, "html.parser")
            except Exception:
                raise
        raise


def find_links_on_page(soup, base_url):
    # Try to find a list of novel links or chapter links.
    anchors = soup.find_all('a', href=True)
    links = []
    for a in anchors:
        href = a['href'].strip()
        if not href:
            continue
        # normalize
        full = urljoin(base_url, href)
        # skip external
        if urlparse(full).netloc != urlparse(base_url).netloc:
            continue
        links.append((a.get_text(strip=True), full))
    # dedupe preserving order
    seen = set()
    out = []
    for text, l in links:
        if l in seen:
            continue
        seen.add(l)
        out.append((text, l))
    return out


def choose_chapter_links(links):
    # Heuristic: choose long lists of links (likely chapter lists)
    # Here we just return the list of unique links; the caller may filter by pattern.
    return [l for _, l in links]


def extract_main_text_from_soup(soup):
    # remove script/style
    for s in soup(['script', 'style', 'noscript', 'header', 'footer', 'nav', 'form']):
        s.decompose()
    # choose the element with most text
    best = soup
    best_len = len(soup.get_text(separator=' ', strip=True))
    for tag in soup.find_all(['div', 'article', 'section'], recursive=True):
        t = tag.get_text(separator=' ', strip=True)
        if len(t) > best_len:
            best = tag
            best_len = len(t)
    text = best.get_text('\n\n', strip=True)
    return text


def download_novel(start_url, out_path, delay=1.0, max_chapters=None):
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    print("Fetching start page:", start_url)
    soup = get_soup(start_url, session)

    links = find_links_on_page(soup, start_url)
    if not links:
        print("No links found on the page.")
        return

    # Heuristic: if many links found (>=5), assume it's a chapter list; otherwise, try to find a link to a chapter-list page
    candidate_chapters = choose_chapter_links(links)

    if len(candidate_chapters) < 5:
        # try to find a page that has many links (e.g., a '目录' link or '章节' text)
        match = None
        for text, l in links:
            if '目录' in text or '章节' in text or '章' in text:
                match = l
                break
        if match:
            print('Found likely TOC page:', match)
            toc_soup = get_soup(match, session)
            toc_links = find_links_on_page(toc_soup, match)
            candidate_chapters = choose_chapter_links(toc_links)

    if not candidate_chapters:
        print('No chapter links found. Exiting.')
        return

    # Optionally limit chapters
    if max_chapters:
        candidate_chapters = candidate_chapters[:max_chapters]

    print(f'Found {len(candidate_chapters)} candidate chapters; starting download...')

    with open(out_path, 'w', encoding='utf-8') as f:
        for idx, chap_url in enumerate(candidate_chapters, 1):
            try:
                print(f'[{idx}/{len(candidate_chapters)}] Fetching', chap_url)
                chap_soup = get_soup(chap_url, session)
                title = chap_soup.title.string.strip() if chap_soup.title and chap_soup.title.string else f'Chapter {idx}'
                text = extract_main_text_from_soup(chap_soup)
                f.write(title + '\n')
                f.write('=' * len(title) + '\n\n')
                f.write(text + '\n\n')
            except Exception as e:
                print('Error fetching', chap_url, e)
            time.sleep(delay)

    print('Download complete ->', out_path)


def main():
    parser = argparse.ArgumentParser(description='Novel downloader (heuristic)')
    parser.add_argument('--url', required=True, help='Start URL (novel page or table-of-contents)')
    parser.add_argument('--output', default='novel.txt', help='Output text file')
    parser.add_argument('--delay', type=float, default=1.0, help='Seconds between requests')
    parser.add_argument('--max-chapters', type=int, default=0, help='Limit number of chapters (0 = no limit)')
    args = parser.parse_args()

    # Legal and polite reminder
    print('\nReminder: only download content you have rights to. Respect site terms.\n')

    download_novel(args.url, args.output, delay=args.delay, max_chapters=(args.max_chapters or None))


if __name__ == '__main__':
    main()
