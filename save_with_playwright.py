#!/usr/bin/env python3
"""
Playwright-based novel downloader.

Usage:
  python save_with_playwright.py --url <novel_or_label_url> --output out.txt --max-chapters 0

Notes:
- This uses Playwright (real browser) which usually bypasses Cloudflare JS challenges.
- Install: `python -m pip install --user playwright` then `python -m playwright install`.
"""
import argparse
import time
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright


def gather_links_from_page(page, base_url):
    anchors = page.query_selector_all('a[href]')
    links = []
    for a in anchors:
        try:
            href = a.get_attribute('href')
        except Exception:
            continue
        if not href:
            continue
        full = urljoin(base_url, href)
        if urlparse(full).netloc != urlparse(base_url).netloc:
            continue
        text = a.inner_text().strip()
        links.append((text, full))
    # dedupe
    seen = set()
    out = []
    for t, l in links:
        if l in seen:
            continue
        seen.add(l)
        out.append((t, l))
    return out


def extract_main_text(page):
    # Try common selectors
    selectors = ['#content', '.content', '.chapter-content', '.read-content', '.entry-content', 'article']
    for sel in selectors:
        try:
            if page.query_selector(sel):
                text = page.inner_text(sel)
                if len(text.strip()) > 100:
                    return text
        except Exception:
            continue
    # fallback to body text
    try:
        return page.inner_text('body')
    except Exception:
        return page.content()


def run(start_url, out_path, headless=True, max_chapters=0, delay=1.0):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
        page = context.new_page()
        print('Opening start URL:', start_url)
        page.goto(start_url, wait_until='networkidle', timeout=60000)

        links = gather_links_from_page(page, start_url)
        chapter_urls = [l for _, l in links]

        if len(chapter_urls) < 5:
            # try to find TOC link
            toc = None
            for text, l in links:
                if '目录' in text or '章节' in text or '章' in text:
                    toc = l
                    break
            if toc:
                print('Opening TOC page:', toc)
                page.goto(toc, wait_until='networkidle', timeout=60000)
                links = gather_links_from_page(page, toc)
                chapter_urls = [l for _, l in links]

        if not chapter_urls:
            print('No chapter links found; will try to extract the page itself.')
            text = extract_main_text(page)
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(text)
            print('Saved single page to', out_path)
            browser.close()
            return

        # Optionally limit
        if max_chapters and max_chapters > 0:
            chapter_urls = chapter_urls[:max_chapters]

        print(f'Found {len(chapter_urls)} chapters; downloading...')
        with open(out_path, 'w', encoding='utf-8') as f:
            for idx, url in enumerate(chapter_urls, 1):
                try:
                    print(f'[{idx}/{len(chapter_urls)}] {url}')
                    page.goto(url, wait_until='networkidle', timeout=60000)
                    title = page.title() or f'Chapter {idx}'
                    text = extract_main_text(page)
                    f.write(title + '\n')
                    f.write('=' * len(title) + '\n\n')
                    f.write(text + '\n\n')
                except Exception as e:
                    print('Error fetching', url, e)
                time.sleep(delay)

        print('Download complete ->', out_path)
        browser.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', default='novel_playwright.txt')
    parser.add_argument('--max-chapters', type=int, default=0)
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--delay', type=float, default=1.0)
    args = parser.parse_args()

    run(args.url, args.output, headless=args.headless, max_chapters=args.max_chapters, delay=args.delay)


if __name__ == '__main__':
    main()
