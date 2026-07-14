#!/usr/bin/env python3
"""
Download all chapters from a content-list page using Playwright.

Usage:
  python download_all_playwright.py --url <start_url> --output book.txt

Notes:
  - Requires Playwright installed: `python -m pip install --user playwright` and
    `python -m playwright install`
  - This script launches a headless browser to bypass JS-based protections.
  - Only use for content you have permission to download.
"""
import argparse
import time
from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright


def gather_links(page, base_url):
    anchors = page.query_selector_all('a[href]')
    links = []
    for a in anchors:
        try:
            href = a.get_attribute('href')
            if not href:
                continue
            href = href.strip()
            if href.startswith('javascript:') or href.startswith('#'):
                continue
            full = urljoin(base_url, href)
            # same domain only
            if urlparse(full).netloc != urlparse(base_url).netloc:
                continue
            text = a.inner_text().strip()
            links.append((text, full))
        except Exception:
            continue
    # dedupe preserving order
    seen = set()
    out = []
    for text, link in links:
        if link in seen:
            continue
        seen.add(link)
        out.append((text, link))
    return out


def choose_chapters(links):
    # Heuristic: prefer links with '章' or numeric sequences or long text
    if not links:
        return []
    # If many links, likely chapter list already
    if len(links) >= 10:
        return [l for _, l in links]

    # otherwise filter by common chapter indicators
    candidates = []
    for text, link in links:
        if '章' in text or '第' in text or 'chapter' in text.lower() or text.isdigit() or len(text) > 2:
            candidates.append(link)
    return candidates or [l for _, l in links]


def extract_text(page):
    selectors = ['#content', '.content', '.chapter-content', '.read-content', '.entry-content', 'article', '.post']
    for sel in selectors:
        try:
            el = page.query_selector(sel)
            if el:
                text = el.inner_text().strip()
                if len(text) > 100:
                    return text
        except Exception:
            continue
    # fallback to body
    try:
        return page.inner_text('body')
    except Exception:
        return page.content()


def download_all(start_url, out_file, headless=True, delay=1.0, timeout_ms=60000, verbose=False):
    def log(*args):
        if verbose:
            print(*args)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
        page = context.new_page()

        log('Opening start URL:', start_url)
        try:
            page.goto(start_url, wait_until='networkidle', timeout=timeout_ms)
        except Exception as e:
            log('Warning: initial goto failed or timed out:', e)

        # show some diagnostics
        try:
            body = page.content()
            log('Start page content size:', len(body))
            if verbose:
                print(body[:1000])
        except Exception as e:
            log('Could not read start page content:', e)

        links = gather_links(page, start_url)
        log('Total links found on start page:', len(links))
        if verbose and links:
            for i, (t, l) in enumerate(links[:20], 1):
                print(f'  {i}. {t} -> {l}')

        chapter_urls = choose_chapters(links)
        log('Candidate chapter URLs:', len(chapter_urls))

        # If still few links, try scanning a 'content list' link
        if len(chapter_urls) < 5:
            toc = None
            for text, link in links:
                if '目录' in text or 'list' in text.lower() or 'content' in text.lower():
                    toc = link
                    break
            if toc:
                log('Opening TOC page:', toc)
                try:
                    page.goto(toc, wait_until='networkidle', timeout=timeout_ms)
                except Exception as e:
                    log('Warning: TOC goto failed:', e)
                links = gather_links(page, toc)
                log('Links on TOC page:', len(links))
                chapter_urls = choose_chapters(links)

        if not chapter_urls:
            log('No chapter links found; saving current page content only.')
            text = extract_text(page)
            with open(out_file, 'w', encoding='utf-8') as f:
                f.write(text)
            log('Saved to', out_file)
            browser.close()
            return

        log(f'Found {len(chapter_urls)} chapters, starting download...')
        # write incrementally
        with open(out_file, 'w', encoding='utf-8') as f:
            for i, url in enumerate(chapter_urls, 1):
                try:
                    log(f'[{i}/{len(chapter_urls)}] Navigating to', url)
                    try:
                        page.goto(url, wait_until='networkidle', timeout=timeout_ms)
                    except Exception as e:
                        log('Warning: goto failed/timed out:', e)
                    title = page.title() or f'Chapter {i}'
                    text = extract_text(page)
                    f.write(title + '\n')
                    f.write('=' * len(title) + '\n\n')
                    f.write(text + '\n\n')
                    f.flush()
                    log('Wrote chapter', i)
                except Exception as e:
                    log('Error fetching', url, e)
                time.sleep(delay)

        log('All done. Saved to', out_file)
        browser.close()


def main():
    parser = argparse.ArgumentParser(description='Download all chapters via Playwright')
    parser.add_argument('--url', required=True, help='Start URL (content list)')
    parser.add_argument('--output', default='book_all.txt')
    parser.add_argument('--headless', action='store_true', help='Run browser headless')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between chapter requests')
    args = parser.parse_args()

    download_all(args.url, args.output, headless=args.headless, delay=args.delay)


if __name__ == '__main__':
    main()
