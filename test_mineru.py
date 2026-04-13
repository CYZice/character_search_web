"""
MinerU 解析 PDF 测试脚本
功能：解析 PDF 前几页，分析字与图片的对应关系
"""

import requests
import time
import os
import re
import zipfile
import io
from pathlib import Path

# ========== 配置 ==========
PDF_PATH = r"C:\Users\Lenovo\Downloads\PDF拆分-自定义范围\遼代漢文石刻文字研究_程玲玲-part0.pdf"
OUTPUT_DIR = Path(r"D:\Microsoft VS Code\lidan\character_search\test_output")
TEST_PAGES = "1-2"  # 先测试 1-2 页

BASE_URL = "https://mineru.net/api/v1/agent"
# ========== 配置 ==========


def parse_pages(file_path: str, page_range: str = None):
    """通过文件上传提交解析任务并等待结果"""
    file_name = file_path.split("/")[-1].split("\\")[-1]

    # 1. 获取签名上传 URL
    data = {
        "file_name": file_name,
        "language": "ch",
        "page_range": page_range,
        "enable_table": False,  # 禁用表格识别，加速
        "is_ocr": True,
        "enable_formula": False,  # 禁用公式识别
    }
    if page_range:
        data["page_range"] = page_range

    print(f"正在提交文件: {file_name}, 页码范围: {page_range}")
    resp = requests.post(f"{BASE_URL}/parse/file", json=data)
    result = resp.json()

    if result["code"] != 0:
        print(f"获取上传链接失败: {result['msg']}")
        return None

    task_id = result["data"]["task_id"]
    file_url = result["data"]["file_url"]
    print(f"任务已创建, task_id: {task_id}")

    # 2. PUT 上传文件到 OSS
    with open(file_path, "rb") as f:
        put_resp = requests.put(file_url, data=f)
        if put_resp.status_code not in (200, 201):
            print(f"文件上传失败, HTTP {put_resp.status_code}")
            return None

    print("文件上传成功，等待解析...")

    # 3. 轮询等待结果
    return poll_result(task_id)


def poll_result(task_id: str, timeout: int = 300, interval: int = 5):
    """轮询查询解析结果"""
    state_labels = {
        "pending": "排队中",
        "running": "解析中",
        "waiting-file": "等待文件上传",
    }

    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(f"{BASE_URL}/parse/{task_id}")
        result = resp.json()

        if result["code"] != 0:
            print(f"查询失败: {result['msg']}")
            return None

        state = result["data"]["state"]
        elapsed = int(time.time() - start)

        if state == "done":
            markdown_url = result["data"]["markdown_url"]
            print(f"[{elapsed}s] 解析完成!")
            return markdown_url

        if state == "failed":
            err_msg = result["data"].get("err_msg", "未知错误")
            print(f"[{elapsed}s] 解析失败: {err_msg}")
            return None

        label = state_labels.get(state, state)
        print(f"[{elapsed}s] {label}...")
        time.sleep(interval)

    print(f"轮询超时 ({timeout}s)，请稍后手动查询 task_id: {task_id}")
    return None


def download_and_analyze(markdown_url: str, output_dir: Path):
    """下载 Markdown 并分析内容"""
    print(f"正在下载 Markdown: {markdown_url}")
    md_resp = requests.get(markdown_url)
    md_content = md_resp.text

    # 保存原始 Markdown
    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / "result.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Markdown 已保存: {md_path}")

    return md_content


def analyze_format(content: str, output_dir: Path):
    """分析 PDF 格式，提取字与图片的对应关系"""
    print("\n" + "=" * 60)
    print("开始分析 PDF 格式...")
    print("=" * 60)

    # 查找被【】框住的字
    char_pattern = re.compile(r"【([^】]+)】")
    chars = char_pattern.findall(content)

    print(f"\n找到 {len(chars)} 个标题字: {chars[:10]}{'...' if len(chars) > 10 else ''}")

    # 查找图片引用（通常是 ![](url) 或本地路径）
    image_pattern = re.compile(r"!\[.*?\]\((.*?)\)")
    images = image_pattern.findall(content)

    print(f"找到 {len(images)} 张图片")

    # 分析 Markdown 结构
    lines = content.split("\n")
    current_char = None
    char_to_images = {}

    for line in lines:
        # 检查是否是标题字行
        char_match = char_pattern.search(line)
        if char_match:
            current_char = char_match.group(1)
            if current_char not in char_to_images:
                char_to_images[current_char] = []

        # 检查是否是图片行
        if line.startswith("!["):
            img_match = image_pattern.search(line)
            if img_match and current_char:
                img_path = img_match.group(1)
                char_to_images[current_char].append(img_path)

    print("\n" + "-" * 40)
    print("字与图片对应关系:")
    print("-" * 40)

    for char, imgs in char_to_images.items():
        print(f"  {char}: {len(imgs)} 张图片")

    # 创建字文件夹并尝试下载图片
    print("\n" + "-" * 40)
    print("创建文件夹结构:")
    print("-" * 40)

    for char, imgs in char_to_images.items():
        char_dir = output_dir / char
        char_dir.mkdir(parents=True, exist_ok=True)
        print(f"  创建文件夹: {char}/")

        # 尝试下载图片（如果是 URL）
        for i, img_url in enumerate(imgs[:5]):  # 限制下载数量
            if img_url.startswith("http"):
                try:
                    img_resp = requests.get(img_url, timeout=10)
                    if img_resp.status_code == 200:
                        # 推断文件扩展名
                        ext = os.path.splitext(img_url.split("?")[0])[1] or ".png"
                        img_path = char_dir / f"{char}_{i + 1}{ext}"
                        with open(img_path, "wb") as f:
                            f.write(img_resp.content)
                        print(f"    下载图片: {img_path.name}")
                except Exception as e:
                    print(f"    下载失败: {img_url[:50]}... ({e})")

    # 生成分析报告
    report_path = output_dir / "analysis_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("PDF 格式分析报告\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"标题字数量: {len(chars)}\n")
        f.write(f"图片数量: {len(images)}\n\n")
        f.write("字与图片对应关系:\n")
        for char, imgs in char_to_images.items():
            f.write(f"  {char}: {len(imgs)} 张图片\n")

    print(f"\n分析报告已保存: {report_path}")

    return char_to_images


def main():
    print("=" * 60)
    print("MinerU PDF 解析测试")
    print("=" * 60)

    # 1. 解析 PDF
    markdown_url = parse_pages(PDF_PATH, TEST_PAGES)

    if not markdown_url:
        print("解析失败!")
        return

    # 2. 下载并分析
    content = download_and_analyze(markdown_url, OUTPUT_DIR)

    # 3. 分析格式
    analyze_format(content, OUTPUT_DIR)

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
