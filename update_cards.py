import os
import sys
import re
import pandas as pd

def _safe_str(v):
    if pd.isna(v):
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

def generate_module_html(module_dir: str, excel_path: str) -> str:
    """读取给定 Excel，生成模块 HTML 内容并返回字符串"""

    module_titles = {
        'education': '教育经历',
        'awards': '竞赛获奖',
        'projects': '项目经验',
        'honors': '校级荣誉',
        'others': '其他经历',
        'student': '学生工作',
        'practice': '社会实践'
    }

    module_name = os.path.splitext(os.path.basename(excel_path))[0]
    display_name = module_titles.get(module_name, module_name)

    try:
        df = pd.read_excel(excel_path)
    except Exception as exc:
        raise RuntimeError(f"无法读取 Excel 文件 {excel_path}: {exc}")

    # 推断列名
    title_col = None
    time_col = None
    desc_cols = []
    image_cols = []

    for col in df.columns:
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
        n = len(df)
        grid_class = 'grid grid-1' if n == 1 else ('grid grid-2' if n == 2 else 'grid grid-3')

    html_lines = []
    # 保留你原有的写法（注意：把 link 放在 innerHTML 里多数浏览器不会生效，
    # 真正生效应在 index.html 的 <head> 引入模块 CSS；此处仅按你的需求保留）
    html_lines.append('<head>')
    html_lines.append('<meta charset="utf-8" />')
    html_lines.append('<meta name="viewport" content="width=device-width, initial-scale=1" />')
    html_lines.append(f'<title>{display_name}</title>')
    html_lines.append(f'<link rel="stylesheet" href="{module_name}.css" />')
    html_lines.append('</head>')

    html_lines.append(f'<section id="{module_name}" class="section">')
    html_lines.append(f'  <h2>{display_name}</h2>')
    html_lines.append(f'  <div class="{grid_class}">')

    for _, row in df.iterrows():
        title = _safe_str(row.get(title_col, ''))
        time = _safe_str(row.get(time_col, ''))

        descriptions = []
        for desc_col in desc_cols:
            d = row.get(desc_col, '')
            d = _safe_str(d)
            if d:
                descriptions.append(d)
        description = "<br>".join(descriptions)

        images = []
        for img_col in image_cols:
            val = row.get(img_col)
            p = _normalize_img_path(val)
            if p:
                images.append(p)

        html_lines.append('    <article class="card">')
        if images:
            html_lines.append('      <div class="image-container">')
            if len(images) > 1:
                html_lines.append('        <div class="image-gallery">')
                for idx, img in enumerate(images):
                    html_lines.append(f'          <img src="{img}" alt="{title} 图片 {idx + 1}" />')
                html_lines.append('        </div>')
            else:
                html_lines.append(f'        <img src="{images[0]}" alt="{title} 图片 1" />')
            html_lines.append('      </div>')
        html_lines.append('      <div class="pad">')
        html_lines.append(f'        <h3>{title}</h3>')
        html_lines.append(f'        <p class="when">{time}</p>')
        if description:
            html_lines.append(f'        <p>{description}</p>')
        html_lines.append('      </div>')
        html_lines.append('    </article>')

    html_lines.append('  </div>')
    html_lines.append('</section>')
    return '\n'.join(html_lines)

def main():
    project_root = os.path.dirname(os.path.abspath(__file__))
    dirs = [name for name in os.listdir(project_root) if os.path.isdir(os.path.join(project_root, name))]
    for module_dir in dirs:
        module_path = os.path.join(project_root, module_dir)
        expected_excel = os.path.join(module_path, f'{module_dir}.xlsx')
        if not os.path.exists(expected_excel):
            continue
        try:
            html_content = generate_module_html(module_path, expected_excel)
        except Exception as exc:
            print(f'生成 {module_dir} 模块失败: {exc}', file=sys.stderr)
            continue
        html_path = os.path.join(module_path, f'{module_dir}.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f'已更新 {module_dir}/{module_dir}.html')

if __name__ == '__main__':
    main()
