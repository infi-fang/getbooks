#!/usr/bin/env python3
"""
Dedicated downloader for miaomiaoks.com novel pages.

Usage:
  python3 download_miaomiaoks.py --url "https://www.miaomiaoks.com/read/240485/" --output "mybook.txt"

  python3 download_miaomiaoks.py --url "https://www.miaomiaoks.com/read/112756/" --output "text.txt"

This script collects all volume pages under a target novel, extracts the main text from each
volume, and writes a single TXT file with clear volume headings.
"""

import argparse
import os
import re
import time
from urllib.parse import urljoin, urlparse

try:
    import requests
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        "Missing dependency: requests. Install project dependencies with 'python3 -m pip install -r requirements.txt'."
    ) from exc

try:
    from bs4 import BeautifulSoup
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        "Missing dependency: beautifulsoup4. Install project dependencies with 'python3 -m pip install -r requirements.txt'."
    ) from exc

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

DEFAULT_FONT_MAPPING_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "font_mapping_simple.json",
)


def get_soup(url, session, timeout=20):
    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def remove_navigation_nodes(soup):
    nav_patterns = re.compile(r"上一章|下一章|没有了|返回目录|章节导航|前一章|后一章|目录|章节列表|章节目录")

    def should_remove(tag, text):
        if not text:
            return False
        if re.search(r"[←→]", text):
            return True
        if tag.name in {"nav", "footer", "a"}:
            return bool(nav_patterns.search(text))

        if tag.name in {"div", "p", "span"}:
            stripped = re.sub(r"\s+", "", text)
            if len(stripped) < 120 and nav_patterns.search(text):
                return True
            if re.fullmatch(r"[←→\s上一章下一章没有了返回目录章节导航前一章后一章目录章节列表章节目录]+", text):
                return True
        return False

    for tag in soup.find_all(["a", "span", "div", "p", "nav", "footer"]):
        text = tag.get_text(" ", strip=True)
        if should_remove(tag, text):
            tag.decompose()
    return soup


def resolve_font_character(src, font_mapping):
    if not font_mapping or not src:
        return None

    src = src.strip()
    if src in font_mapping:
        return font_mapping[src]

    m = re.search(r"/asset/fonts/(\d+)\.png", src)
    if m and m.group(1) in font_mapping:
        return font_mapping[m.group(1)]

    m = re.search(r"(\d+)\.png$", src)
    if m and m.group(1) in font_mapping:
        return font_mapping[m.group(1)]

    return None


def replace_image_tags_with_text(el, font_mapping=None):
    for img in el.find_all("img"):
        src = img.get("src", "")
        mapped_text = resolve_font_character(src, font_mapping)
        if mapped_text is not None:
            img.replace_with(mapped_text)
            continue

        if font_mapping:
            img.replace_with("")
            continue

        text = img.get("alt") or img.get("title") or img.get("aria-label") or ""
        if not text:
            m = re.search(r"/asset/fonts/(\d+)\.png", src)
            if m:
                text = f"[[{m.group(1)}]]"
            else:
                text = "*"
        img.replace_with(text)
    return el


def extract_text_from_section(soup, font_mapping=None):
    for cls in ["content", "chapter-content", "read-content", "book-content"]:
        el = soup.find("div", class_=cls)
        if el:
            replace_image_tags_with_text(el, font_mapping)
            paragraphs = [
                p.get_text(" ", strip=True)
                for p in el.find_all("p", recursive=False)
                if p.get_text(" ", strip=True)
            ]
            if paragraphs:
                return clean_text("\n\n".join(paragraphs))

            text = el.get_text(" ", strip=True)
            if len(text) > 50:
                return clean_text(text)

    el = soup.find("article") or soup.body
    if el:
        replace_image_tags_with_text(el, font_mapping)
        paragraphs = [
            p.get_text(" ", strip=True)
            for p in el.find_all("p", recursive=False)
            if p.get_text(" ", strip=True)
        ]
        if paragraphs:
            return clean_text("\n\n".join(paragraphs))

        text = el.get_text(" ", strip=True)
        if len(text) > 50:
            return clean_text(text)
    return ""


def extract_text_from_soup(soup, font_mapping=None):
    text = extract_text_from_section(soup, font_mapping)
    if text:
        return text
    cleaned = extract_text_from_section(remove_navigation_nodes(soup), font_mapping)
    return cleaned


def clean_text(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.splitlines()]

    def normalize_spacing(line):
        line = re.sub(r"[\t ]+", " ", line)
        line = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", line)
        line = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[，。！？；：,.!?;:])", "", line)
        line = re.sub(r"(?<=[，。！？；：,.!?;:])\s+(?=[\u4e00-\u9fff])", "", line)
        return line.strip()

    def is_navigation_line(line):
        if not line:
            return False
        if "取消转码/退出阅读模式" in line and "作者:" in line and "字数:" in line:
            return True
        if re.match(r"^如果出现文字缺失.*退出阅读模式.*作者:.*字数:\d+.*\*+$", line):
            return True
        if re.search(r"[←→]", line):
            return True
        if re.search(r"上一章|下一章|没有了|返回目录|章节导航|前一章|后一章|目录|章节列表", line):
            return True
        return False

    def split_boilerplate(line):
        match = re.match(
            r"^(如果出现文字缺失，格式混乱请取消转码/退出阅读模式\s*作者:[^字]+字数:\d+\s*\*+)(.*)$",
            line,
        )
        if match:
            head = match.group(1).strip()
            tail = match.group(2).strip()
            if tail:
                return [("boilerplate", head), ("body", tail)]
            return [("boilerplate", head)]
        return [("body", line)]

    paragraphs = []
    current = []

    def flush_current():
        if not current:
            return
        paragraph = "\n".join(current)
        if paragraph:
            paragraphs.append(paragraph)
        current.clear()

    for line in lines:
        line = normalize_spacing(line)
        if not line:
            flush_current()
            continue

        for piece_type, piece in split_boilerplate(line):
            if not piece:
                flush_current()
                continue
            if piece_type == "boilerplate":
                flush_current()
                paragraphs.append(piece)
                continue
            if is_navigation_line(piece):
                flush_current()
                continue
            current.append(piece)

    flush_current()

    return "\n\n".join(paragraphs)


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


def load_font_mapping_file(path):
    import json
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    normalized = {}
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                char = value.get("character") or value.get("char") or value.get("value")
            else:
                char = value

            if not isinstance(char, str):
                continue

            normalized[str(key)] = char

            m = re.search(r"/asset/fonts/(\d+)\.png", str(key))
            if m:
                normalized[m.group(1)] = char

            m = re.search(r"(\d+)\.png$", str(key))
            if m:
                normalized[m.group(1)] = char

    return normalized


def apply_font_mapping(text, mapping):
    def replace_match(match):
        font_id = match.group(1)
        return mapping.get(font_id, mapping.get(str(font_id))) or match.group(0)

    return re.sub(r"\[\[(\d+)\]\]", replace_match, text)


def download_miaomiaoks(url, output_path, delay=1.0, max_volumes=0, font_mapping_path=None):
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    font_mapping = None
    if font_mapping_path:
        font_mapping = load_font_mapping_file(font_mapping_path)

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
            text = extract_text_from_soup(volume_soup, font_mapping)
            if not text:
                print("Warning: 未提取到内容，跳过", link)
                continue

            if font_mapping:
                text = apply_font_mapping(text, font_mapping)

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
    parser.add_argument("--font-mapping", help="Optional JSON file with font ID to character mappings")
    args = parser.parse_args()

    font_mapping_path = args.font_mapping
    if not font_mapping_path and os.path.exists(DEFAULT_FONT_MAPPING_PATH):
        font_mapping_path = DEFAULT_FONT_MAPPING_PATH

    download_miaomiaoks(
        args.url,
        args.output,
        delay=args.delay,
        max_volumes=args.max_volumes,
        font_mapping_path=font_mapping_path,
    )


if __name__ == "__main__":
    main()
