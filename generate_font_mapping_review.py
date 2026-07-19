#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

DEFAULT_FONT_COUNT = 104


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_html(path, html):
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def build_font_ids(contexts, max_font_id=DEFAULT_FONT_COUNT):
    ids = set(str(k) for k in contexts.keys())
    ids.update(str(i) for i in range(0, max_font_id + 1))
    return sorted(ids, key=lambda x: (int(x), x))


def build_html(entries, output_path, title="miaomiaoks font mapping review"):
    rows = []
    for font_id, entry in entries:
        contexts = entry.get("contexts", [])
        image_html = f'<img src="fonts/{font_id}.png" alt="{font_id}" loading="lazy">' if entry.get("has_image") else '<div class="missing">missing image</div>'
        context_html = "".join(f"<li>{ctx}</li>" for ctx in contexts[:5])
        if len(contexts) > 5:
            context_html += f"<li>... {len(contexts)} total contexts</li>"
        rows.append(f"""
          <div class="item" data-id="{font_id}">
            <div class="image">{image_html}</div>
            <div class="id">ID {font_id}</div>
            <div class="field">
              <label>Mapped char</label>
              <input type="text" name="char-{font_id}" placeholder="输入字符或留空" />
            </div>
            <div class="contexts">
              <strong>Contexts</strong>
              <ol>{context_html}</ol>
            </div>
          </div>
        """)

    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 16px; }
    h1 { margin-bottom: 8px; }
    .toolbar { margin-bottom: 16px; }
    .toolbar button { margin-right: 8px; padding: 8px 12px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; }
    .item { border: 1px solid #ccc; border-radius: 8px; padding: 12px; background: #fff; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
    .image { text-align: center; margin-bottom: 8px; min-height: 100px; }
    .image img { max-width: 100%; max-height: 120px; object-fit: contain; }
    .missing { color: #888; padding: 36px 0; }
    .id { font-weight: bold; margin-bottom: 8px; }
    .field label { display: block; margin-bottom: 4px; font-size: 13px; color: #333; }
    .field input { width: 100%; padding: 6px 8px; font-size: 14px; border: 1px solid #ccc; border-radius: 4px; }
    .contexts { margin-top: 12px; font-size: 13px; line-height: 1.5; }
    .contexts strong { display: block; margin-bottom: 6px; }
    .contexts ol { padding-left: 18px; margin: 0; }
    .contexts li { margin-bottom: 4px; }
    #output-json { width: 100%; min-height: 160px; margin-top: 12px; font-family: monospace; white-space: pre-wrap; word-break: break-all; }
  </style>
</head>
<body>
  <h1>{title}</h1>
  <div class="toolbar">
    <button id="build-json">生成映射 JSON</button>
    <button id="copy-json">复制 JSON</button>
    <button id="download-json">下载 JSON</button>
  </div>
  <div class="grid">
    {rows}
  </div>
  <h2>结果 JSON</h2>
  <textarea id="output-json" readonly></textarea>
  <script>
    const buildButton = document.getElementById('build-json');
    const copyButton = document.getElementById('copy-json');
    const downloadButton = document.getElementById('download-json');
    const output = document.getElementById('output-json');

    function buildMapping() {
      const mapping = {};
      document.querySelectorAll('.item').forEach(item => {
        const id = item.dataset.id;
        const input = item.querySelector('input');
        const value = input.value.trim();
        mapping[id] = value || null;
      });
      output.value = JSON.stringify(mapping, null, 2);
    }

    buildButton.addEventListener('click', buildMapping);
    copyButton.addEventListener('click', () => {
      output.select();
      document.execCommand('copy');
    });
    downloadButton.addEventListener('click', () => {
      buildMapping();
      const blob = new Blob([output.value], { type: 'application/json;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'font_mapping.json';
      a.click();
      URL.revokeObjectURL(url);
    });
  </script>
</body>
</html>"""
    html = html.replace("{title}", title).replace("{rows}", ''.join(rows))
    save_html(output_path, html)


def main():
    parser = argparse.ArgumentParser(description="Generate a review HTML for miaomiaoks font image mapping.")
    parser.add_argument("--contexts", default="font_contexts.json", help="Font context JSON file")
    parser.add_argument("--output", default="font_mapping_review.html", help="Output HTML filename")
    parser.add_argument("--max-font-id", type=int, default=DEFAULT_FONT_COUNT, help="Maximum font ID to include")
    parser.add_argument("--fonts-dir", default="fonts", help="Local font images directory")
    args = parser.parse_args()

    contexts_path = Path(args.contexts)
    if not contexts_path.exists():
        raise FileNotFoundError(f"Contexts file not found: {contexts_path}")

    data = load_json(contexts_path)
    contexts = data.get('contexts', data)
    if not isinstance(contexts, dict):
        raise ValueError('Unsupported contexts format, expected JSON object with a contexts mapping.')

    entries = []
    for font_id in build_font_ids(contexts, max_font_id=args.max_font_id):
        font_info = {
            'contexts': contexts.get(font_id, []),
            'has_image': Path(args.fonts_dir, f"{font_id}.png").exists(),
        }
        entries.append((font_id, font_info))

    build_html(entries, args.output)
    print(f"Generated review HTML: {args.output}")


if __name__ == '__main__':
    main()
