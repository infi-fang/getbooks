#!/usr/bin/env python3
"""
Download all articles linked from a directory/TOC page into a single TXT.

Usage:
  python download_directory.py --url <toc_url> --output book.txt

Options:
  --delay FLOAT       seconds between requests (default 0.8)
  --max-chapters INT  limit number of chapters (0 = no limit)
  --user-agent STR    custom User-Agent header
  --cookies COOKIES   cookies string for requests (e.g. "k=v; k2=v2")

Notes:
- Designed for pages without heavy anti-bot protections.
- Respect site terms and copyright.
"""
import argparse
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
)


def make_session(user_agent=None, cookies=None):
    s = requests.Session()
    s.headers.update({"User-Agent": user_agent or DEFAULT_UA})
    if cookies:
        # cookies string like "k=v; k2=v2"
        jar = requests.cookies.RequestsCookieJar()
        for part in cookies.split(';'):
            if '=' in part:
                k, v = part.split('=', 1)
                jar.set(k.strip(), v.strip())
        s.cookies = jar
    return s


def get_soup(url, session, timeout=20):
    r = session.get(url, timeout=timeout)
    r.raise_for_status()
    return BeautifulSoup(r.text, 'html.parser')


def find_links(soup, base_url):
    anchors = soup.find_all('a', href=True)
    links = []
    for a in anchors:
        href = a['href'].strip()
        if not href or href.startswith('javascript:') or href.startswith('#'):
            continue
        full = urljoin(base_url, href)
        if urlparse(full).netloc != urlparse(base_url).netloc:
            continue
        text = a.get_text(strip=True)
        links.append((text, full))
    # dedupe preserving order
    seen = set()
    out = []
    for t, l in links:
        if l in seen:
            continue
        seen.add(l)
        out.append((t or l, l))
    return out


def filter_chapters(links):
    if not links:
        return []
    # If many links, assume they are chapters
    if len(links) >= 8:
        return [l for _, l in links]
    # otherwise prefer ones with chapter indicators
    candidates = []
    for t, l in links:
        tl = t.lower()
        if '章' in t or '第' in t or 'chapter' in tl or '节' in t or tl.strip().isdigit():
            candidates.append(l)
    return candidates or [l for _, l in links]


def extract_text(soup):
    # try common containers
    selectors = ['#content', '.content', '.chapter-content', '.read-content', '.entry-content', 'article']
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            text = el.get_text('\n', strip=True)
            if len(text) > 80:
                return text
    # fallback to largest div
    best = None
    best_len = 0
    for div in soup.find_all(['div', 'article', 'section']):
        t = div.get_text('\n', strip=True)
        if len(t) > best_len:
            best_len = len(t)
            best = t
    if best_len > 0:
        return best
    return soup.get_text('\n', strip=True)


def download_directory(url, out_path, delay=0.8, max_chapters=0, user_agent=None, cookies=None):
    sess = make_session(user_agent, cookies)
    print('Fetching directory page:', url)
    soup = get_soup(url, sess)
    links = find_links(soup, url)
    print(f'Found {len(links)} total links on page')
    chapter_urls = filter_chapters(links)
    print(f'Filtered to {len(chapter_urls)} candidate chapter links')

    if max_chapters and max_chapters > 0:
        chapter_urls = chapter_urls[:max_chapters]

    if not chapter_urls:
        print('No chapter links discovered; saving page content only.')
        text = extract_text(soup)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(text)
        print('Saved:', out_path)
        return

    with open(out_path, 'w', encoding='utf-8') as out:
        for i, link in enumerate(chapter_urls, 1):
            try:
                print(f'[{i}/{len(chapter_urls)}] GET {link}')
                ch_soup = get_soup(link, sess)
                title = (ch_soup.title.string.strip() if ch_soup.title and ch_soup.title.string else f'Chapter {i}')
                text = extract_text(ch_soup)
                out.write(title + '\n')
                out.write('=' * len(title) + '\n\n')
                out.write(text + '\n\n')
            except Exception as e:
                print('Error fetching', link, e)
            out.flush()
            time.sleep(delay)

    print('All chapters saved to', out_path)


def main():
    parser = argparse.ArgumentParser(description='Download articles from a directory/TOC page')
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', default='book.txt')
    parser.add_argument('--delay', type=float, default=0.8)
    parser.add_argument('--max-chapters', type=int, default=0)
    parser.add_argument('--user-agent', default=None)
    parser.add_argument('--cookies', default=None)
    args = parser.parse_args()

    download_directory(args.url, args.output, delay=args.delay, max_chapters=args.max_chapters, user_agent=args.user_agent, cookies=args.cookies)


if __name__ == '__main__':
    main()
