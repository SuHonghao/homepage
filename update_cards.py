import os
import sys
import re
import json
from html import escape
from pathlib import Path
from openpyxl import load_workbook

MODULES = ("education", "internship", "publications", "projects", "awards", "honors", "student", "practice", "others")
MODULE_LABELS = ("EDUCATION", "INTERNSHIP", "PUBLICATIONS", "SELECTED WORK", "AWARDS", "HONORS", "CAMPUS", "VOLUNTEERING", "EXPERIENCE")

def _safe_str(v):
    if v is None:
        return ""
    if isinstance(v, (int, float)):
        # 整数不带小数，浮点保留两位(但去掉结尾.00)
        s = f"{v:.2f}" if isinstance(v, float) else str(v)
        return s.rstrip("0").rstrip(".") if "." in s else s
    return str(v).strip()

def _normalize_img_path(p):
    # 把 \ 换成 /，避免浏览器路径问题
    return _safe_str(p).replace("\\", "/")

def _detect_columns_from_css(module_dir: str, module_name: str) -> int | None:
    """
    优先根据 #{module} .grid-N 规则判断；若没有，尝试解析 repeat(N, ...)。
    找不到则返回 None。
    """
    css_path = os.path.join(module_dir, f"{module_name}.css")
    if not os.path.exists(css_path):
        return None

    try:
        css = open(css_path, "r", encoding="utf-8").read()
    except Exception:
        return None

    # 1) 直接找选择器里是否出现 #{module} .grid-N
    #    支持 #education .grid-3、#awards .grid-2 等
    pat_selector = re.compile(rf"#{re.escape(module_name)}\s*\.grid-(\d+)")
    nums = [int(m.group(1)) for m in pat_selector.finditer(css)]
    if nums:
        # 有多个的话取最大（更“强”的布局）
        return max(nums)

    # 2) 在 #{module} 作用域内找 grid-template-columns: repeat(N, ...)
    #    简化处理：全局扫描 repeat(N, 的 N
    pat_repeat = re.compile(r"grid-template-columns\s*:\s*repeat\(\s*(\d+)\s*,", re.I)
    nums2 = [int(m.group(1)) for m in pat_repeat.finditer(css)]
    if nums2:
        return max(nums2)

    return None

def generate_module_html(module_dir: str, excel_path: str, content=None) -> str:
    """读取给定 Excel，生成模块 HTML 内容并返回字符串"""

    module_titles = {
        'education': '教育经历',
        'internship': '实习经历',
        'publications': '主要论文',
        'awards': '竞赛获奖',
        'projects': '项目经验',
        'honors': '校级荣誉',
        'others': '其他经历',
        'student': '学生工作',
        'practice': '社会实践'
    }

    module_name = os.path.splitext(os.path.basename(excel_path))[0]
    display_name = module_titles.get(module_name, module_name)

    if content is not None:
        columns = ['title', 'time', 'description', 'image1', 'image2']
        records = []
        for item in content:
            record = dict(item)
            record['description'] = '\n'.join(item.get('descriptions', []))
            for index, image in enumerate(item.get('images', []), 1):
                record[f'image{index}'] = image
                if f'image{index}' not in columns:
                    columns.append(f'image{index}')
            records.append(record)
    else:
        try:
            workbook = load_workbook(excel_path, read_only=True, data_only=True)
            try:
                rows = list(workbook.active.values)
            finally:
                workbook.close()
            columns = rows[0]
            records = [dict(zip(columns, row)) for row in rows[1:] if any(v is not None for v in row)]
        except Exception as exc:
            raise RuntimeError(f"无法读取 Excel 文件 {excel_path}: {exc}")

    # 推断列名
    title_col = None
    time_col = None
    desc_cols = []
    image_cols = []

    for col in columns:
        col_lower = _safe_str(col).lower()
        if not title_col and (col_lower.startswith('标题') or col_lower.startswith('title')):
            title_col = col
        elif not time_col and (col_lower.startswith('时间') or col_lower.startswith('time')):
            time_col = col
        elif col_lower.startswith('描述') or col_lower.startswith('description'):
            desc_cols.append(col)
        if col_lower.startswith('图片') or col_lower.startswith('image'):
            image_cols.append(col)

    if not title_col or not time_col:
        raise ValueError(f"Excel {excel_path} 缺少必要的列（标题和时间）")

    # —— NEW: 按模块 CSS 决定列数；否则回退到条目数量逻辑 ——
    cols_from_css = _detect_columns_from_css(module_dir, module_name)
    if cols_from_css in (1, 2, 3, 4, 5, 6):
        grid_class = f"grid grid-{cols_from_css}"
    else:
        # 回退策略：1条=1列；2条=2列；>=3条=3列
        n = len(records)
        grid_class = 'grid grid-1' if n == 1 else ('grid grid-2' if n == 2 else 'grid grid-3')

    html_lines = []
    html_lines.append(f'<section id="{module_name}" class="section">')
    section_index = MODULES.index(module_name)
    label = f'{section_index + 1:02d} / {MODULE_LABELS[section_index]}'
    html_lines.append(f'  <h2 data-label="{label}">{display_name}</h2>')
    html_lines.append(f'  <div class="{grid_class}">')

    for row in records:
        title = escape(_safe_str(row.get(title_col, '')))
        time = escape(_safe_str(row.get(time_col, '')))

        descriptions = []
        for desc_col in desc_cols:
            d = row.get(desc_col, '')
            d = _safe_str(d)
            if d:
                descriptions.append(escape(d).replace("\n", "<br>"))
        description = "<br>".join(descriptions)

        images = []
        for img_col in image_cols:
            val = row.get(img_col)
            p = _normalize_img_path(val)
            if p:
                # 表格中的本地占位路径可能没有对应文件，不输出破图。
                if not p.startswith(('https://', 'http://', 'data:')) and not (Path(module_dir).parent / p).is_file():
                    print(f"跳过不存在的图片: {p}", file=sys.stderr)
                    continue
                images.append(escape(p, quote=True))

        card_class = 'card' if images else 'card text-only'
        html_lines.append(f'    <article class="{card_class}">')
        if images:
            html_lines.append('      <div class="image-container">')
            if len(images) > 1:
                html_lines.append('        <div class="image-gallery">')
                for idx, img in enumerate(images):
                    html_lines.append(f'          <img loading="lazy" decoding="async" src="{img}" alt="{title} 图片 {idx + 1}" />')
                html_lines.append('        </div>')
            else:
                html_lines.append(f'        <img loading="lazy" decoding="async" src="{images[0]}" alt="{title} 图片 1" />')
            html_lines.append('      </div>')
        html_lines.append('      <div class="pad">')
        html_lines.append(f'        <h3>{title}</h3>')
        if row.get('role'):
            html_lines.append(f'<p class="author-role">{escape(row["role"])}</p>')
        if time:
            html_lines.append(f'        <p class="when">{time}</p>')
        if description:
            html_lines.append(f'        <p>{description}</p>')
        if row.get('links'):
            html_lines.append('<div class="resource-links">')
            for link in row['links']:
                if link['url'].startswith('https://'):
                    html_lines.append(f'<a href="{escape(link["url"], quote=True)}" target="_blank" rel="noopener noreferrer">{escape(link["label"])} ↗</a>')
            html_lines.append('</div>')
        html_lines.append('      </div>')
        html_lines.append('    </article>')

    html_lines.append('  </div>')
    html_lines.append('</section>')
    return '\n'.join(html_lines)

def main():
    project_root = Path(__file__).resolve().parent
    content_path = project_root / 'data/cv-content.json'
    content = json.loads(content_path.read_text(encoding='utf-8')) if content_path.exists() else {}
    sections = []
    for module in MODULES:
        module_path = project_root / module
        section = generate_module_html(str(module_path), str(module_path / f"{module}.xlsx"), content.get(module))
        sections.append(section)
        # 独立模块页面与主页共用根目录资源，file:// 和子路径部署均可用。
        styles = ["styles/base.css", "styles/cards.css", "styles/images.css",
                  f"{module}/{module}.css", "styles/responsive.css", "styles/theme.css"]
        links = "\n".join(f'<link rel="stylesheet" href="{css}" />' for css in styles)
        document = ('<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n'
                    '<meta charset="utf-8" />\n<base href="../" />\n'
                    '<meta name="viewport" content="width=device-width, initial-scale=1" />\n'
                    f'<title>{re.search(r"<h2[^>]*>(.*?)</h2>", section).group(1)}</title>\n'
                    f'{links}\n</head>\n<body>\n<main class="container">\n{section}\n'
                    '</main>\n<script src="script.js" defer></script>\n</body>\n</html>\n')
        (module_path / f"{module}.html").write_text(document, encoding="utf-8")
        print(f"已更新 {module}/{module}.html")

    index_path = project_root / "index.html"
    index = index_path.read_text(encoding="utf-8")
    index, count = re.subn(
        r'(<main class="container" id="modules-wrapper">).*?(</main>)',
        lambda match: match[1] + "\n" + "\n".join(sections) + "\n  " + match[2],
        index, flags=re.S)
    if count != 1:
        raise RuntimeError("index.html 缺少唯一的 modules-wrapper")
    index_path.write_text(index, encoding="utf-8")
    print("已同步 index.html")

if __name__ == '__main__':
    main()
