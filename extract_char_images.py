"""
MinerU 精准解析 API - 字与图片对应提取 v2
每个图片的命名为: {字}_{出处}_{序号}.jpg
出处为图片后面紧跟的小字（paragraph）
"""

import requests
import time
import os
import re
import json
import shutil
from pathlib import Path

# ========== 配置 ==========
PDF_PATH = r"C:\Users\Lenovo\Downloads\辽代汉文石刻字形.docx"
OUTPUT_DIR = Path(r"D:\Microsoft VS Code\lidan\character_search\output_word")
TOKEN = "eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFM1MTIifQ.eyJqdGkiOiI3NDEwMDY5MiIsInJvbCI6IlJPTEVfUkVHSVNURVIiLCJpc3MiOiJPcGVuWExhYiIsImlhdCI6MTc3NTcyODg3NCwiY2xpZW50SWQiOiJsa3pkeDU3bnZ5MjJqa3BxOXgydyIsInBob25lIjoiIiwib3BlbklkIjpudWxsLCJ1dWlkIjoiZmRjZDZhYTEtY2M5Ni00NzI1LWE4YWItMmNiNzRkZTQ4ODljIiwiZW1haWwiOiIiLCJleHAiOjE3ODM1MDQ4NzR9.qAjuXVV73cCmIb5OyGhKiCMMonE1rSIOFKafUTPaqOlx2sxyAViTK25e39NZ5tCD7oKY9rBkvO76msIM6UiJIQ"
BASE_URL = "https://mineru.net/api/v4"
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"}
# ========== 配置 ==========


def create_and_poll_task(file_path: str):
    """创建任务并轮询结果"""
    file_name = os.path.basename(file_path)

    # 1. 申请上传链接
    url = f"{BASE_URL}/file-urls/batch"
    data = {"files": [{"name": file_name, "data_id": "test_pdf"}], "model_version": "vlm"}

    resp = requests.post(url, headers=headers, json=data)
    result = resp.json()

    if result["code"] != 0:
        print(f"申请上传链接失败: {result['msg']}")
        return None

    batch_id = result["data"]["batch_id"]
    upload_url = result["data"]["file_urls"][0]
    print(f"batch_id: {batch_id}")

    # 2. 上传文件
    with open(file_path, "rb") as f:
        put_resp = requests.put(upload_url, data=f)
    print("文件上传成功!" if put_resp.status_code == 200 else f"上传失败: {put_resp.status_code}")

    # 3. 轮询结果
    return poll_result(batch_id)


def poll_result(batch_id: str, timeout: int = 600, interval: int = 10):
    """轮询批量任务结果"""
    start = time.time()

    while time.time() - start < timeout:
        url = f"{BASE_URL}/extract-results/batch/{batch_id}"
        resp = requests.get(url, headers=headers)
        result = resp.json()

        if result["code"] != 0:
            print(f"查询失败: {result['msg']}")
            return None

        for item in result["data"].get("extract_result", []):
            state = item.get("state")
            if state == "done":
                print(f"解析完成! [{int(time.time()-start)}s]")
                return item.get("full_zip_url")
            elif state == "running":
                prog = item.get("extract_progress", {})
                print(f"解析中: {prog.get('extracted_pages',0)}/{prog.get('total_pages',0)} 页...")
            elif state == "failed":
                print(f"失败: {item.get('err_msg')}")

        time.sleep(interval)

    return None


def download_and_extract(zip_url: str, output_dir: Path):
    """下载并解压 zip"""
    output_dir.mkdir(parents=True, exist_ok=True)
    import zipfile, io

    resp = requests.get(zip_url, timeout=60)
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        zf.extractall(output_dir)

    print(f"解压到: {output_dir}")
    return output_dir


def sanitize_filename(name: str) -> str:
    """清理文件名，移除非法字符"""
    # 移除或替换非法字符
    illegal_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in illegal_chars:
        name = name.replace(char, '_')
    # 限制长度
    if len(name) > 100:
        name = name[:100]
    return name


def is_valid_char_title(text: str) -> bool:
    """
    判断是否是有效的汉字标题（被【】框住的单个或少量字符）
    过滤掉：
    - 章节标题如"第一卷"、"第一部"等
    - 部首分类如"丄部"等
    - 其他非目标标题
    """
    # 必须被【】框住
    if not re.match(r"^【([^】]+)】$", text):
        return False

    char = text[1:-1]  # 提取【】内的内容

    # 过滤章节标题模式（第一x、第xx等）
    if re.match(r"^第[一二三四五六七八九十百千萬]+", char):
        return False

    # 过滤常见的部首/分类标题
    invalid_titles = ["一部", "丄部", "通用", "附录", "索引"]
    if char in invalid_titles:
        return False

    # 过滤太长的标题（正常的字标题应该是1-4个字符左右）
    if len(char) > 6:
        return False

    return True


def extract_char_image_mapping(content_list_path: Path, base_dir: Path):
    """
    从 content_list_v2.json 提取字与图片的对应关系 v2

    PDF 格式：
    - 【标题字】是 title 类型
    - 标题字后面紧跟的 image blocks 属于该标题字
    - 每个 image 后面紧跟的 paragraph 是该图片的出处

    返回: {
        '字': [
            {'image': Path, 'source': '出处文字'},
            ...
        ],
        ...
    }
    """
    with open(content_list_path, "r", encoding="utf-8") as f:
        blocks = json.load(f)

    # 展平嵌套结构
    def flatten(lst):
        result = []
        for item in lst:
            if isinstance(item, list):
                result.extend(flatten(item))
            elif isinstance(item, dict):
                result.append(item)
        return result

    flat_blocks = flatten(blocks)

    char_to_images = {}
    current_char = None

    i = 0
    while i < len(flat_blocks):
        block = flat_blocks[i]
        block_type = block.get("type", "")

        if block_type == "title":
            # 提取新的标题字
            content = block.get("content", {})
            title_content = content.get("title_content", [])
            for tc in title_content:
                if tc.get("type") == "text":
                    text = tc.get("content", "")
                    # 只处理【】框住的标题字
                    if is_valid_char_title(text):
                        current_char = text[1:-1]  # 去掉【】
                        if current_char not in char_to_images:
                            char_to_images[current_char] = []
                        print(f"找到标题字: 【{current_char}】")
                    else:
                        # 如果遇到无效标题，重置 current_char
                        if current_char is not None:
                            print(f"  [跳过非汉字标题: {text}]")
                        current_char = None
                    break

        elif block_type == "image" and current_char:
            # 图片属于当前标题字
            img_path = block.get("content", {}).get("image_source", {}).get("path", "")
            if img_path:
                full_path = base_dir / img_path

                # 查看下一个 block 是否是同一行的出处文字
                source_text = ""
                if i + 1 < len(flat_blocks):
                    next_block = flat_blocks[i + 1]
                    if next_block.get("type") == "paragraph":
                        para_content = next_block.get("content", {})
                        para_list = para_content.get("paragraph_content", [])
                        for p in para_list:
                            if p.get("type") == "text":
                                source_text = p.get("content", "").strip()
                                break

                char_to_images[current_char].append({
                    "image": full_path,
                    "source": source_text
                })

        i += 1

    return char_to_images


def save_char_images(char_to_images: dict, output_dir: Path):
    """为每个字创建文件夹并复制图片，命名为 {字}_{出处}_{序号}.jpg"""

    # 首先统计每个字每个出处的图片数量（用于序号）
    source_counts = {}

    for char, images in char_to_images.items():
        for img_info in images:
            source = img_info.get("source", "") or "未知出处"
            key = (char, source)
            if key not in source_counts:
                source_counts[key] = 0
            source_counts[key] += 1

    # 复制图片
    for char, images in char_to_images.items():
        char_dir = output_dir / char
        char_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n【{char}】: {len(images)} 张图片")

        # 按出处分组
        source_to_images = {}
        for img_info in images:
            source = img_info.get("source", "") or "未知出处"
            if source not in source_to_images:
                source_to_images[source] = []
            source_to_images[source].append(img_info)

        for source, imgs in source_to_images.items():
            # 每个出处单独一个子文件夹或序号
            safe_source = sanitize_filename(source)

            for i, img_info in enumerate(imgs):
                img_path = img_info["image"]
                if img_path.exists():
                    ext = img_path.suffix or ".jpg"
                    # 命名为: {字}_{出处}_{序号}.jpg
                    filename = f"{char}_{safe_source}_{i+1:03d}{ext}"
                    filename = sanitize_filename(filename)
                    dest = char_dir / filename
                    shutil.copy2(img_path, dest)
                    print(f"  -> {filename}")
                else:
                    print(f"  [缺失] {img_path}")


def generate_report(char_to_images: dict, output_dir: Path):
    """生成详细报告"""
    report_path = output_dir / "char_image_mapping.txt"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("字与图片对应关系报告\n")
        f.write("=" * 60 + "\n\n")

        for char, images in char_to_images.items():
            f.write(f"【{char}】: {len(images)} 张图片\n")

            source_to_images = {}
            for img_info in images:
                source = img_info.get("source", "") or "未知出处"
                if source not in source_to_images:
                    source_to_images[source] = []
                source_to_images[source].append(img_info["image"].name)

            for source, img_names in source_to_images.items():
                f.write(f"  出处: {source}\n")
                for name in img_names:
                    f.write(f"    - {name}\n")
            f.write("\n")

    print(f"\n报告已保存: {report_path}")


def main():
    print("=" * 60)
    print("MinerU 精准解析 API - 字图对应提取 v2")
    print("=" * 60)

    # 1. 解析 PDF
    zip_url = create_and_poll_task(PDF_PATH)
    if not zip_url:
        return

    # 2. 下载解压
    extract_dir = download_and_extract(zip_url, OUTPUT_DIR)

    # 3. 提取对应关系
    content_list_path = extract_dir / "content_list_v2.json"

    if content_list_path.exists():
        char_to_images = extract_char_image_mapping(content_list_path, extract_dir)

        # 4. 保存结果
        save_char_images(char_to_images, OUTPUT_DIR)

        # 5. 生成报告
        generate_report(char_to_images, OUTPUT_DIR)

    print("\n完成!")


if __name__ == "__main__":
    main()
