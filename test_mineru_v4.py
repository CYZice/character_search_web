"""
MinerU 精准解析 API - 字与图片对应提取
根据 PDF 格式：标题字【】后面紧跟的图片属于该字
"""

import requests
import time
import os
import re
import json
import shutil
from pathlib import Path

# ========== 配置 ==========
PDF_PATH = r"C:\Users\Lenovo\Downloads\PDF拆分-自定义范围\遼代漢文石刻文字研究_程玲玲-part0.pdf"
OUTPUT_DIR = Path(r"D:\Microsoft VS Code\lidan\character_search\test_output_v4")
TEST_PAGES = "1-2"

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


def extract_char_image_mapping(content_list_path: Path, base_dir: Path):
    """
    从 content_list_v2.json 提取字与图片的对应关系

    PDF 格式：
    - 【标题字】是 title 类型
    - 标题字后面紧跟的 image blocks 属于该标题字
    - 直到遇到下一个 title 或页面结束
    """
    with open(content_list_path, "r", encoding="utf-8") as f:
        blocks = json.load(f)

    # 展平嵌套结构（有些是 [[blocks...]] 或 [[[blocks...]]]）
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
    current_images = []

    for block in flat_blocks:
        block_type = block.get("type", "")

        if block_type == "title":
            # 保存上一个字的数据
            if current_char and current_images:
                if current_char not in char_to_images:
                    char_to_images[current_char] = []
                char_to_images[current_char].extend(current_images)

            # 提取新的标题字
            content = block.get("content", {})
            title_content = content.get("title_content", [])
            for tc in title_content:
                if tc.get("type") == "text":
                    text = tc.get("content", "")
                    match = re.search(r"【([^】]+)】", text)
                    if match:
                        current_char = match.group(1)
                        current_images = []
                        print(f"找到标题字: 【{current_char}】")
                        break

        elif block_type == "image" and current_char:
            # 图片属于当前标题字
            # JSON 中的路径是 "images/xxx.jpg"，需要拼接在 base_dir 下
            img_path = block.get("content", {}).get("image_source", {}).get("path", "")
            if img_path:
                # img_path 格式: "images/xxx.jpg"
                full_path = base_dir / img_path
                current_images.append(full_path)

    # 保存最后一个字的数据
    if current_char and current_images:
        if current_char not in char_to_images:
            char_to_images[current_char] = []
        char_to_images[current_char].extend(current_images)

    return char_to_images


def save_char_images(char_to_images: dict, output_dir: Path):
    """为每个字创建文件夹并复制图片"""
    for char, images in char_to_images.items():
        char_dir = output_dir / char
        char_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n【{char}】: {len(images)} 张图片")
        for i, img_path in enumerate(images):
            if img_path.exists():
                ext = img_path.suffix or ".jpg"
                dest = char_dir / f"{char}_{i+1:03d}{ext}"
                shutil.copy2(img_path, dest)
                print(f"  -> {dest.name}")
            else:
                print(f"  [缺失] {img_path}")


def main():
    print("=" * 60)
    print("MinerU 精准解析 API - 字图对应提取")
    print("=" * 60)

    # 1. 解析 PDF
    zip_url = create_and_poll_task(PDF_PATH)
    if not zip_url:
        return

    # 2. 下载解压
    extract_dir = download_and_extract(zip_url, OUTPUT_DIR)

    # 3. 提取对应关系
    content_list_path = extract_dir / "content_list_v2.json"
    images_dir = extract_dir / "images"

    if content_list_path.exists():
        char_to_images = extract_char_image_mapping(content_list_path, extract_dir)

        # 4. 保存结果
        save_char_images(char_to_images, extract_dir)

        # 5. 生成报告
        report_path = extract_dir / "char_image_mapping.txt"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("字与图片对应关系\n")
            f.write("=" * 50 + "\n")
            for char, images in char_to_images.items():
                f.write(f"【{char}】: {len(images)} 张图片\n")
                for img in images:
                    f.write(f"  - {img.name}\n")
        print(f"\n报告已保存: {report_path}")

    print("\n完成!")


if __name__ == "__main__":
    main()
