"""
Import script: 从MinerU输出目录导入图片到数据库
1. 解析content_list_v2.json，建立字-图对应关系
2. 复制图片到data/{字}/目录，命名为{字}_{出处}_{序号}.jpg
3. 导入数据库
"""
import sys
import re
import json
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal, engine
from app import models, crud

# 创建表
models.Base.metadata.create_all(bind=engine)

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent / "output"


def is_valid_char_title(text: str) -> bool:
    """判断是否是有效的汉字标题"""
    if not re.match(r"^【([^】]+)】$", text):
        return False
    char = text[1:-1]
    # 过滤章节标题
    if re.match(r"^第[一二三四五六七八九十百千萬]+", char):
        return False
    # 过滤常见分类标题
    invalid = ["一部", "丄部", "通用", "附录", "索引"]
    if char in invalid:
        return False
    # 过滤太长的
    if len(char) > 6:
        return False
    return True


def flatten(lst):
    """展平嵌套结构"""
    result = []
    for item in lst:
        if isinstance(item, list):
            result.extend(flatten(item))
        elif isinstance(item, dict):
            result.append(item)
    return result


def import_from_output_v4():
    """V4 格式导入 - 处理 MinerU v4 API 返回的 JSON"""
    import glob

    # {char: [(image_path, source_text, json_dir), ...]}
    char_images = {}
    current_char = None
    pending_image = None

    # 处理所有 *_content_list.json 文件（递归查找子目录）
    json_files = sorted(OUTPUT_DIR.rglob("*_content_list.json"))
    print(f"找到 {len(json_files)} 个 JSON 文件")

    for json_file in json_files:
        json_dir = json_file.parent
        print(f"处理: {json_file.relative_to(OUTPUT_DIR)}")
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        for block in data:
            block_type = block.get("type", "")

            # V4 格式: text_level=1 是标题
            if block_type == "text" and block.get("text_level") == 1:
                text = block.get("text", "")
                if is_valid_char_title(text):
                    # 处理上一个字的暂存图片
                    if pending_image and current_char:
                        if current_char not in char_images:
                            char_images[current_char] = []
                        char_images[current_char].append(pending_image)
                        pending_image = None

                    current_char = text[1:-1]
                    if current_char not in char_images:
                        char_images[current_char] = []

            elif block_type == "image" and current_char:
                img_path = block.get("img_path", "")
                if img_path:
                    pending_image = (img_path, "", json_dir)

            elif block_type == "text" and block.get("text_level") is None and pending_image:
                source = block.get("text", "").strip()
                if source:
                    pending_image = (pending_image[0], source, pending_image[2])
                    if current_char:
                        char_images[current_char].append(pending_image)
                    pending_image = None

    # 处理最后一个暂存图片
    if pending_image and current_char:
        if current_char not in char_images:
            char_images[current_char] = []
        char_images[current_char].append(pending_image)

    print(f"找到 {len(char_images)} 个汉字")
    return char_images


def import_from_output_v2():
    """V2 格式导入 - 处理旧版 content_list_v2.json（递归查找子目录）"""
    # 递归查找所有 content_list_v2.json 文件
    json_files = sorted(OUTPUT_DIR.rglob("content_list_v2.json"))
    if not json_files:
        print(f"JSON文件不存在: {OUTPUT_DIR / 'content_list_v2.json'}")
        return None

    # 建立字-图对应关系
    char_images = {}  # {char: [(image_path, source_text, json_dir), ...]}

    for json_path in json_files:
        json_dir = json_path.parent
        print(f"处理: {json_path.relative_to(OUTPUT_DIR)}")

        # 读取JSON
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        flat_blocks = flatten(data)
        print(f"  共 {len(flat_blocks)} 个block")

        current_char = None
        pending_image = None  # 暂存未处理出处的图片

        i = 0
        while i < len(flat_blocks):
            block = flat_blocks[i]
            block_type = block.get("type", "")

            if block_type == "title":
                content = block.get("content", {})
                title_content = content.get("title_content", [])
                for tc in title_content:
                    if tc.get("type") == "text":
                        text = tc.get("content", "")
                        if is_valid_char_title(text):
                            current_char = text[1:-1]  # 去掉【】
                            if current_char not in char_images:
                                char_images[current_char] = []
                            # 处理暂存的图片（上一个字的）
                            if pending_image and current_char:
                                char_images[current_char].append(pending_image)
                                pending_image = None
                        break

            elif block_type == "image" and current_char:
                img_rel_path = block.get("content", {}).get("image_source", {}).get("path", "")
                if img_rel_path:
                    pending_image = (img_rel_path, "", json_dir)

            elif block_type == "paragraph" and pending_image:
                para_content = block.get("content", {}).get("paragraph_content", [])
                for p in para_content:
                    if p.get("type") == "text":
                        source = p.get("content", "").strip()
                        pending_image = (pending_image[0], source, pending_image[2])
                        break
                # 图片属于当前字
                if current_char and current_char in char_images:
                    char_images[current_char].append(pending_image)
                pending_image = None

            i += 1

        # 处理最后一个暂存图片
        if pending_image and current_char:
            if current_char not in char_images:
                char_images[current_char] = []
            char_images[current_char].append(pending_image)

    print(f"找到 {len(char_images)} 个汉字")
    return char_images


def import_from_output():
    """从output目录导入"""
    if not OUTPUT_DIR.exists():
        print(f"输出目录不存在: {OUTPUT_DIR}")
        return

    # 创建data目录
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 检测格式：优先使用 V4 格式（*_content_list.json 文件）
    v4_files = list(OUTPUT_DIR.rglob("*_content_list.json"))
    if v4_files:
        print("检测到 V4 格式 JSON，使用 V4 导入逻辑")
        char_images = import_from_output_v4()
    else:
        print("使用 V2 格式导入")
        char_images = import_from_output_v2()

    if not char_images:
        print("没有找到汉字数据")
        return

    # 导入数据库并复制文件
    db = SessionLocal()
    try:
        total_new_chars = 0
        total_new_images = 0
        total_skipped = 0
        total_missing = 0

        for char, images in sorted(char_images.items()):
            # 获取或创建 Character 记录
            db_char = crud.get_character_by_name(db, char)
            if db_char is None:
                db_char = crud.get_or_create_character(db, char)
                total_new_chars += 1
                print(f"\n新增汉字: 【{char}】 ({len(images)} 张图片)")
            else:
                print(f"\n更新汉字: 【{char}】")

            # 获取该汉字已有的图片路径（用于去重）
            existing_paths = {img.image_path for img in db_char.images}
            next_order = len(db_char.images)  # 追加到现有图片之后

            # 创建图片目录
            char_dir = DATA_DIR / char
            char_dir.mkdir(exist_ok=True)

            new_count = 0
            for (img_rel_path, source, json_dir) in images:
                # 去重：检查该图片路径是否已存在
                if img_rel_path in existing_paths:
                    total_skipped += 1
                    continue

                # 源文件（图片路径相对于 JSON 文件所在目录）
                src_path = json_dir / img_rel_path
                if not src_path.exists():
                    total_missing += 1
                    continue

                # 目标文件命名: {字}_{出处}_{序号}.jpg
                safe_source = re.sub(r'[<>:"/\\|?*]', '_', source)[:50] if source else "无出处"
                filename = f"{char}_{safe_source}_{next_order+1:03d}.jpg"
                dest_path = char_dir / filename

                # 复制文件
                if not dest_path.exists():
                    shutil.copy2(src_path, dest_path)

                # 相对路径
                rel_path = f"{char}/{filename}"

                crud.create_character_image(
                    db,
                    db_char.id,
                    rel_path,
                    source,
                    next_order
                )
                existing_paths.add(rel_path)  # 防止同一批次内重复
                next_order += 1
                new_count += 1
                total_new_images += 1

            if new_count > 0:
                print(f"  -> 新增 {new_count} 张图片")

        db.commit()
        print(f"\n导入完成!")
        print(f"新增汉字: {total_new_chars} 个")
        print(f"新增图片: {total_new_images} 张")
        print(f"跳过(已存在): {total_skipped} 张")
        print(f"缺失(文件不存在): {total_missing} 张")
        print(f"数据目录: {DATA_DIR}")

    finally:
        db.close()


if __name__ == "__main__":
    import sys
    # 支持外部指定OUTPUT_DIR
    if len(sys.argv) > 1:
        output_dir = Path(sys.argv[1])
        OUTPUT_DIR = output_dir
    import_from_output()
