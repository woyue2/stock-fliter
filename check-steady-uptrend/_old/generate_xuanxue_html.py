import argparse
import os
import re
from html import escape
from typing import Optional


def parse_table_stocks(md_text, board_name: Optional[str] = None):
    lines = md_text.splitlines()
    header_idx = None
    code_idx = name_idx = board_idx = None

    for i, line in enumerate(lines):
        if line.strip().startswith("|") and "代码" in line and "名称" in line:
            header_idx = i
            headers = [p.strip() for p in line.strip().strip("|").split("|")]
            for j, h in enumerate(headers):
                if h == "代码":
                    code_idx = j
                elif h == "名称":
                    name_idx = j
                elif h == "板块":
                    board_idx = j
            break

    if header_idx is None or code_idx is None or name_idx is None:
        return []

    rows = []
    for line in lines[header_idx + 2 :]:
        if not line.strip().startswith("|"):
            break
        parts = [p.strip() for p in line.strip().strip("|").split("|")]
        if len(parts) <= max(code_idx, name_idx):
            continue
        code_raw = parts[code_idx]
        name = parts[name_idx]
        board = parts[board_idx] if board_idx is not None and board_idx < len(parts) else ""
        code_match = re.search(r"\d{6}", code_raw)
        if not code_match:
            continue
        code = code_match.group(0)
        if board_name and board_name != "ALL" and board != board_name:
            continue
        rows.append((code, name, board))
    return rows


def infer_market_prefix(code: str, board: Optional[str] = None) -> str:
    board = (board or "").strip()
    if board in {"上海主板", "科创板"}:
        return "sh"
    if board in {"深圳主板", "创业板"}:
        return "sz"
    if board in {"北交所", "北京交易所"}:
        return "bj"
    if code.startswith("6"):
        return "sh"
    if code.startswith("8"):
        return "bj"
    return "sz"


def add_links_to_markdown(md_text: str) -> str:
    lines = md_text.splitlines()
    header_idx = None
    code_idx = name_idx = board_idx = None

    for i, line in enumerate(lines):
        if line.strip().startswith("|") and "代码" in line and "名称" in line:
            header_idx = i
            headers = [p.strip() for p in line.strip().strip("|").split("|")]
            for j, h in enumerate(headers):
                if h == "代码":
                    code_idx = j
                elif h == "名称":
                    name_idx = j
                elif h == "板块":
                    board_idx = j
            break

    if header_idx is None or code_idx is None or name_idx is None:
        return md_text

    out_lines = lines[:]
    for i in range(header_idx + 2, len(lines)):
        line = lines[i]
        if not line.strip().startswith("|"):
            break
        parts = [p.strip() for p in line.strip().strip("|").split("|")]
        if len(parts) <= max(code_idx, name_idx):
            continue

        code_raw = parts[code_idx]
        name_raw = parts[name_idx]
        board = parts[board_idx] if board_idx is not None and board_idx < len(parts) else ""

        code_match = re.search(r"\d{6}", code_raw)
        if not code_match:
            continue
        code = code_match.group(0)
        prefix = infer_market_prefix(code, board)
        url = f"https://quote.eastmoney.com/{prefix}{code}.html"

        parts[code_idx] = f"[{code}]({url})"
        if name_raw:
            parts[name_idx] = f"[{name_raw}]({url})"

        out_lines[i] = "| " + " | ".join(parts) + " |"

    return "\n".join(out_lines)


def build_html(title, source_md, stocks, board_name: Optional[str] = None):
    if not stocks:
        raise ValueError("No stocks found for the requested board.")

    first_code, _, first_board = stocks[0]
    first_prefix = infer_market_prefix(first_code, first_board)
    first_url = f"https://quote.eastmoney.com/{first_prefix}{first_code}.html"

    list_items = []
    for code, name, board in stocks:
        prefix = infer_market_prefix(code, board)
        url = f"https://quote.eastmoney.com/{prefix}{code}.html"
        list_items.append(
            "        <li><label><input type=\"checkbox\" /> "
            f"<a href=\"{escape(url)}\" target=\"quoteFrame\">"
            f"<span class=\"code\">{escape(code)}</span> - {escape(name)}"
            f" <span class=\"board\">{escape(board)}</span></a></label></li>"
        )

    html = f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{escape(title)}</title>
  <style>
    :root {{
      color-scheme: light dark;
    }}
    body {{
      font-family: \"Segoe UI\", \"PingFang SC\", \"Microsoft YaHei\", Arial, sans-serif;
      margin: 24px;
      line-height: 1.6;
    }}
    h1 {{
      margin-bottom: 8px;
    }}
    .meta {{
      color: #666;
      margin-bottom: 16px;
    }}
    ul {{
      padding-left: 20px;
    }}
    a {{
      text-decoration: none;
    }}
    a:hover {{
      text-decoration: underline;
    }}
    .code {{
      font-weight: 600;
    }}
    .layout {{
      display: grid;
      grid-template-columns: minmax(260px, 360px) 1fr;
      gap: 16px;
      align-items: start;
    }}
    .list-panel {{
      max-height: 80vh;
      overflow: auto;
      padding-right: 4px;
    }}
    .preview-panel {{
      border: 1px solid #ccc;
      border-radius: 8px;
      overflow: hidden;
      background: #fff;
      min-height: 80vh;
    }}
    iframe {{
      width: 100%;
      height: 80vh;
      border: 0;
    }}
  </style>
</head>
<body>
  <h1>{escape(title)}</h1>
    <div class=\"meta\">来源：{escape(source_md)}（板块过滤：{escape(board_name or 'ALL')}）</div>

  <div class=\"layout\">
    <nav class=\"list-panel\">
      <ul>
{os.linesep.join(list_items)}
      </ul>
    </nav>
    <section class=\"preview-panel\">
      <iframe name=\"quoteFrame\" title=\"股票行情预览\" src=\"{escape(first_url)}\"></iframe>
    </section>
  </div>
</body>
</html>
"""
    return html


def main():
    parser = argparse.ArgumentParser(description="Generate xuanxue HTML preview from md.")
    parser.add_argument("--md", required=True, help="Path to xuanxue markdown file")
    parser.add_argument("--out", help="Output HTML path")
    parser.add_argument("--board", default="ALL", help="Board name filter")
    parser.add_argument("--title", help="HTML title")
    parser.add_argument("--all", action="store_true", help="Generate HTML for all markdown files in the same folder")

    args = parser.parse_args()

    md_paths = [args.md]
    if args.all:
        md_dir = os.path.dirname(args.md) or "."
        md_paths = [os.path.join(md_dir, f) for f in os.listdir(md_dir) if f.lower().endswith(".md")]

    for md_path in md_paths:
        with open(md_path, "r", encoding="utf-8") as f:
            md_text = f.read()

        stocks = parse_table_stocks(md_text, args.board)

        md_basename = os.path.basename(md_path)
        title = args.title or f"{os.path.splitext(md_basename)[0]} - {args.board}"
        html = build_html(title, md_basename, stocks, board_name=args.board)

        if args.out and not args.all and md_path == args.md:
            out_path = args.out
        else:
            base, _ = os.path.splitext(md_path)
            out_path = f"{base}.html"

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"Generated: {out_path}")


if __name__ == "__main__":
    main()
