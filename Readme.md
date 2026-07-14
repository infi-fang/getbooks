# getbooks

## 项目介绍

`getbooks` 是一个轻量级的小说/文本内容下载工具集合，主要用于从网页目录页、章节页或特定小说站点抓取文本并保存为 `.txt` 文件。项目包含多个 Python 脚本，分别适配不同场景：普通 HTML 抓取、基于 Playwright 的浏览器抓取、特定站点抓取等。

> 仅用于合法内容的下载。请尊重网站版权、服务条款和 robots.txt，避免滥用自动化抓取。

## 目录结构

- `save_novel.py`：通用小说抓取脚本，基于 `requests` + `BeautifulSoup`，适合常规目录页与章节列表。
- `save_with_playwright.py`：Playwright 版本抓取，适用于需要执行 JavaScript、绕过简单防爬或页面渲染的场景。
- `download_all_playwright.py`：从内容列表页下载所有章节，使用 Playwright 浏览器抓取。
- `download_directory.py`：从目录/TOC 页面下载所有文章或章节列表。
- `download_miaomiaoks.py`：专门针对 `miaomiaoks.com` 网站的小说下载器。
- `*.txt`：示例输出文件和历史下载结果。

## 依赖

推荐使用 Python 3.8 及以上。

基础依赖：

- `requests`
- `beautifulsoup4`

Playwright 相关脚本需要额外安装：

```bash
python -m pip install --user playwright
python -m playwright install
```

如果使用 `save_with_playwright.py` 或 `download_all_playwright.py`，请确认 Playwright 已正确安装。

## 使用说明

### 1. `save_novel.py`

通用小说抓取脚本，适用于普通目录页或小说首页。

```bash
python save_novel.py --url <novel_page_or_toc_url> --output mybook.txt
```

可选参数：

- `--delay`：章节请求间隔，默认 `1.0` 秒。
- `--max-chapters`：限制下载章节数量，`0` 表示不限制。

示例：

```bash
python save_novel.py --url "https://book.xbookcn.net/search/label/附体记" --output mybook.txt --delay 1.5 --max-chapters 20
```

### 2. `save_with_playwright.py`

基于 Playwright 的抓取，适用于需要 JS 渲染或 Cloudflare 保护的页面。

```bash
python save_with_playwright.py --url <novel_page_or_toc_url> --output mybook_playwright.txt
```

可选参数：

- `--max-chapters`：最多抓取章节数，默认 `0`（全部）。
- `--headless`：启动无头浏览器（默认可选）。
- `--delay`：章节请求间隔，默认 `1.0` 秒。

示例：

```bash
python save_with_playwright.py --url "https://book.xbookcn.net/search/label/附体记" --output mybook_playwright.txt --max-chapters 5 --headless --delay 1
```

### 3. `download_all_playwright.py`

从内容列表页下载所有可用章节，适合整本小说或完整目录抓取。

```bash
python download_all_playwright.py --url <content_list_url> --output full_book.txt
```

可选参数：

- `--headless`：启用无头浏览器模式。
- `--delay`：章节请求间隔，默认 `1.0` 秒。

示例：

```bash
python download_all_playwright.py --url "https://www.example.com/contentlist_xxx.html" --output full_book.txt --headless --delay 1
```

### 4. `download_directory.py`

从目录/TOC 页面下载所有章节或文章。

```bash
python download_directory.py --url <toc_url> --output book.txt
```

可选参数：

- `--delay`：请求间隔，默认 `0.8` 秒。
- `--max-chapters`：最大章节数，默认 `0`。
- `--user-agent`：自定义 User-Agent。
- `--cookies`：传入 Cookie 字符串，例如 `"k=v; k2=v2"`。

示例：

```bash
python download_directory.py --url "https://www.example.com/toc.html" --output book.txt --delay 1.0 --max-chapters 50
```

### 5. `download_miaomiaoks.py`

专门用于 `miaomiaoks.com` 网站。

```bash
python download_miaomiaoks.py --url "https://www.miaomiaoks.com/read/105519/" --output miaomiaoks_105519.txt
```

可选参数：

- `--delay`：请求间隔，默认 `1.0` 秒。
- `--max-volumes`：限制下载分卷数量，默认 `0`（全部）。

示例：

```bash
python download_miaomiaoks.py --url "https://www.miaomiaoks.com/read/105519/" --output miaomiaoks_105519.txt --delay 1.0 --max-volumes 10
```

## 运行前建议

- 先确认目标网站是否允许自动抓取。
- 将请求间隔设置为 `0.8` 秒以上，避免触发反爬机制。
- 如果页面需要登录或 Cookie，可使用 `download_directory.py` 的 `--cookies` 参数。
- 对于 JS 渲染或保护较强的页面，优先使用 `save_with_playwright.py` 或 `download_all_playwright.py`。

## 注意事项

- 本项目仅提供抓取工具，不保证对所有网站都有效。
- 如果某个页面结构与脚本规则不匹配，可能需要调整脚本或手动提取。
- 请勿用于未经授权的商业用途。

## 示例命令

```bash
python download_all_playwright.py --url "https://www.xn--1jqvh729avzfcy2d8ummib.com/contentlist_53da7f3192c957f199365cef25b5e94d.html" --output "C:\Dev\Workspace\getbooks\full_book.txt" --headless --delay 1
python3 save_novel.py --url "https://book.xbookcn.net/search/label/%E9%99%84%E4%BD%93%E8%AE%B0" --output mybook.txt
python save_with_playwright.py --url "https://book.xbookcn.net/search/label/%E9%99%84%E4%BD%93%E8%AE%B0" --output mybook_playwright.txt --max-chapters 5 --headless --delay 1
python download_miaomiaoks.py --url "https://www.miaomiaoks.com/read/105519/" --output "miaomiaoks_105519.txt" --delay 1
```
