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


def import_from_output():
    """从output目录导入"""
    if not OUTPUT_DIR.exists():
        print(f"输出目录不存在: {OUTPUT_DIR}")
        return

    json_path = OUTPUT_DIR / "content_list_v2.json"
    if not json_path.exists():
        print(f"JSON文件不存在: {json_path}")
        return

    # 创建data目录
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 读取JSON
    print("读取JSON...")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    flat_blocks = flatten(data)
    print(f"共 {len(flat_blocks)} 个block")

    # 建立字-图对应关系
    char_images = {}  # {char: [(image_path, source_text), ...]}
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
                pending_image = (img_rel_path, "")

        elif block_type == "paragraph" and pending_image:
            para_content = block.get("content", {}).get("paragraph_content", [])
            for p in para_content:
                if p.get("type") == "text":
                    source = p.get("content", "").strip()
                    pending_image = (pending_image[0], source)
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

    # 导入数据库并复制文件
    db = SessionLocal()
    try:
        total_images = 0

        for char, images in sorted(char_images.items()):
            print(f"\n处理汉字: 【{char}】 ({len(images)} 张图片)")

            # 创建或更新Character记录
            db_char = crud.get_character_by_name(db, char)
            if db_char is None:
                db_char = crud.create_character(db, char)
            else:
                crud.delete_character_images(db, db_char.id)

            # 创建图片目录
            char_dir = DATA_DIR / char
            char_dir.mkdir(exist_ok=True)

            for idx, (img_rel_path, source) in enumerate(images):
                # 源文件
                src_path = OUTPUT_DIR / img_rel_path
                if not src_path.exists():
                    continue

                # 目标文件命名: {字}_{出处}_{序号}.jpg
                safe_source = re.sub(r'[<>:"/\\|?*]', '_', source)[:50] if source else "无出处"
                filename = f"{char}_{safe_source}_{idx+1:03d}.jpg"
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
                    idx
                )
                total_images += 1

        db.commit()
        print(f"\n导入完成!")
        print(f"共 {len(char_images)} 个汉字")
        print(f"共 {total_images} 张图片")
        print(f"数据目录: {DATA_DIR}")

    finally:
        db.close()


if __name__ == "__main__":
    import_from_output()
