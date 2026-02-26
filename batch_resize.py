#!/usr/bin/env python3
"""
batch_resize.py

批量调整文件夹内图片尺寸。

示例：
  python batch_resize.py --input ./photos --output ./out --width 800 --height 600 --mode cover --quality 85 --keep-structure

模式:
  cover   - 裁切并填满目标尺寸（图片居中裁切）
  contain - 缩放到目标尺寸内，留空白（可指定背景颜色）
  stretch - 强制拉伸到目标尺寸（可能变形）

依赖:
  pip install pillow
"""
import argparse
import os
from pathlib import Path
from PIL import Image, ImageOps
import concurrent.futures

SUPPORTED_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tiff'}


def process_image(src_path: Path, dest_path: Path, width: int, height: int, mode: str, bg_color: str, quality: int, overwrite: bool):
    try:
        if dest_path.exists() and not overwrite:
            return f"skip (exists): {dest_path}"

        with Image.open(src_path) as img:
            img_format = img.format or dest_path.suffix.replace('.', '').upper()

            if mode == 'stretch':
                out = img.resize((width, height), Image.LANCZOS)

            elif mode == 'contain':
                # 保持比例，放在目标画布中央，背景为 bg_color
                img.thumbnail((width, height), Image.LANCZOS)
                out = Image.new('RGBA' if img.mode in ('RGBA','LA') else 'RGB', (width, height), bg_color)
                # 处理透明 PNG 的背景选择：如果目标格式支持 alpha，保留；否则合并背景色
                if img.mode in ('RGBA', 'LA'):
                    out = Image.new('RGBA', (width, height), bg_color)
                    out.paste(img, ((width - img.width) // 2, (height - img.height) // 2), img)
                else:
                    out.paste(img, ((width - img.width) // 2, (height - img.height) // 2))

            elif mode == 'cover':
                # 裁切实现：先按比例放大直到覆盖目标，再居中裁切
                src_w, src_h = img.size
                scale = max(width / src_w, height / src_h)
                new_size = (int(src_w * scale + 0.5), int(src_h * scale + 0.5))
                img_resized = img.resize(new_size, Image.LANCZOS)
                left = (img_resized.width - width) // 2
                top = (img_resized.height - height) // 2
                out = img_resized.crop((left, top, left + width, top + height))
            else:
                return f"error (unknown mode): {mode}"

            # 若目标为非透明格式但 out 为 RGBA，合并背景色
            ext = dest_path.suffix.lower()
            if out.mode == 'RGBA' and ext in ('.jpg', '.jpeg'):
                # 合并背景色并转换为 RGB
                bg = Image.new('RGB', out.size, bg_color)
                bg.paste(out, mask=out.split()[3])  # 3 is alpha
                out = bg

            dest_path.parent.mkdir(parents=True, exist_ok=True)

            save_params = {}
            if ext in ('.jpg', '.jpeg'):
                save_params['quality'] = quality
                save_params['optimize'] = True
            if ext == '.webp':
                save_params['quality'] = quality
            # For PNG you can add optimize=True but it may be slow.

            # PIL expects format name like 'JPEG' or 'PNG'
            fmt = None
            if img_format:
                fmt = img_format
            else:
                fmt = dest_path.suffix.replace('.', '').upper()

            # Ensure correct mode for saving formats
            if fmt.upper() in ('JPEG', 'JPG') and out.mode == 'RGBA':
                out = out.convert('RGB')

            out.save(dest_path, format=fmt, **save_params)
            return f"ok: {dest_path}"
    except Exception as e:
        return f"error: {src_path} -> {e}"


def gather_images(input_dir: Path, recursive: bool):
    files = []
    if recursive:
        for p in input_dir.rglob('*'):
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
                files.append(p)
    else:
        for p in input_dir.iterdir():
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
                files.append(p)
    return sorted(files)


def main():
    p = argparse.ArgumentParser(description="Batch resize images in a folder.")
    p.add_argument('--input', '-i', required=True, help='Input folder containing images')
    p.add_argument('--output', '-o', required=True, help='Output folder for resized images')
    p.add_argument('--width', '-W', type=int, required=True, help='Target width in pixels')
    p.add_argument('--height', '-H', type=int, required=True, help='Target height in pixels')
    p.add_argument('--mode', '-m', choices=('cover','contain','stretch'), default='cover', help='Resize mode')
    p.add_argument('--bg', default='#ffffff', help='Background color for contain mode or flattening (hex or name)')
    p.add_argument('--quality', '-q', type=int, default=85, help='Quality for JPEG/WEBP (0-100)')
    p.add_argument('--recursive', '-r', action='store_true', help='Process subdirectories recursively')
    p.add_argument('--keep-structure', action='store_true', help='Keep directory structure under output')
    p.add_argument('--overwrite', action='store_true', help='Overwrite existing files in output')
    p.add_argument('--workers', type=int, default=4, help='Number of worker threads (parallel processing)')
    args = p.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)
    if not input_dir.exists() or not input_dir.is_dir():
        print("输入文件夹不存在或不是目录:", input_dir)
        return

    files = gather_images(input_dir, args.recursive)
    if not files:
        print("未找到支持的图片文件。")
        return

    tasks = []
    for src in files:
        if args.keep_structure:
            try:
                rel = src.relative_to(input_dir)
            except Exception:
                rel = src.name
            dest = output_dir.joinpath(rel)
        else:
            dest = output_dir.joinpath(src.name)
        tasks.append((src, dest))

    print(f"Found {len(tasks)} images. Mode={args.mode}, size={args.width}x{args.height}, workers={args.workers}")

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = []
        for src, dest in tasks:
            futures.append(ex.submit(process_image, src, dest, args.width, args.height, args.mode, args.bg, args.quality, args.overwrite))
        for f in concurrent.futures.as_completed(futures):
            print(f.result())

    print("Done.")


if __name__ == '__main__':
    main()


