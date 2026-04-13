"""
MinerU 精准解析 API - 逐个处理PDF并即时导入数据库
每个PDF独立文件夹，互不干扰
"""

import requests
import time
import os
import json
import zipfile
import io
import logging
from pathlib import Path
from datetime import datetime

# ========== 日志配置 ==========
LOG_DIR = Path(r"D:\Microsoft VS Code\lidan\character_search\logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

log_file = LOG_DIR / f"process_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
# ========== 日志配置 ==========

# ========== 配置 ==========
PDF_LIST = [
    r"C:\Users\Lenovo\Downloads\PDF拆分-自定义范围\遼代漢文石刻文字研究_程玲玲-part0.pdf",
    r"C:\Users\Lenovo\Downloads\PDF拆分-自定义范围\遼代漢文石刻文字研究_程玲玲-part1.pdf",
    r"C:\Users\Lenovo\Downloads\PDF拆分-自定义范围\遼代漢文石刻文字研究_程玲玲-part2.pdf",
    r"C:\Users\Lenovo\Downloads\PDF拆分-自定义范围\遼代漢文石刻文字研究_程玲玲-part3.pdf",
]
BASE_OUTPUT_DIR = Path(r"D:\Microsoft VS Code\lidan\character_search\output")
IMPORT_SCRIPT = Path(__file__).parent / "scripts" / "import_content_list.py"

TOKEN = "eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFM1MTIifQ.eyJqdGkiOiI3NDEwMDY5MiIsInJvbCI6IlJPTEVfUkVHSVNURVIiLCJpc3MiOiJPcGVuWExhYiIsImlhdCI6MTc3NjA1NTI2OCwiY2xpZW50SWQiOiJsa3pkeDU3bnZ5MjJqa3BxOXgydyIsInBob25lIjoiIiwib3BlbklkIjpudWxsLCJ1dWlkIjoiMGUxNTFhMzQtNjQ0OS00MTE4LTk4ZWEtMWEyNGI1ZjYyN2UyIiwiZW1haWwiOiIiLCJleHAiOjE3ODM4MzEyNjh9.qR0-K4RjKW3USdLSZ8fdNa0vCOlkgZxtC5SatjRvnfyQ5WR0NZuTghmFcURTJ3IzNAyl5IO18nP88EnTpnirJQ"
BASE_URL = "https://mineru.net/api/v4"
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"}
# ========== 配置 ==========


def create_and_poll_task(file_path: str):
    """创建任务并轮询结果"""
    file_name = os.path.basename(file_path)

    # 1. 申请上传链接
    url = f"{BASE_URL}/file-urls/batch"
    data = {
        "files": [{"name": file_name, "data_id": "pdf_char"}],
        "model_version": "vlm",
    }

    resp = requests.post(url, headers=headers, json=data)
    result = resp.json()

    if result["code"] != 0:
        logger.error(f"申请上传链接失败: {result['msg']}")
        return None

    batch_id = result["data"]["batch_id"]
    upload_url = result["data"]["file_urls"][0]
    logger.info(f"batch_id: {batch_id}")

    # 2. 上传文件
    with open(file_path, "rb") as f:
        put_resp = requests.put(upload_url, data=f)
    if put_resp.status_code == 200:
        logger.info("文件上传成功!")
    else:
        logger.error(f"上传失败: {put_resp.status_code}")
        return None

    # 3. 轮询结果
    return poll_result(batch_id)


def poll_result(batch_id: str, timeout: int = 1200, interval: int = 15):
    """轮询批量任务结果"""
    start = time.time()

    while time.time() - start < timeout:
        url = f"{BASE_URL}/extract-results/batch/{batch_id}"
        resp = requests.get(url, headers=headers)
        result = resp.json()

        if result["code"] != 0:
            logger.error(f"查询失败: {result['msg']}")
            return None

        for item in result["data"].get("extract_result", []):
            state = item.get("state")
            if state == "done":
                elapsed = int(time.time() - start)
                logger.info(f"解析完成! [{elapsed}s]")
                return item.get("full_zip_url")
            elif state == "running":
                prog = item.get("extract_progress", {})
                logger.info(
                    f"解析中: {prog.get('extracted_pages',0)}/{prog.get('total_pages',0)} 页..."
                )
            elif state == "failed":
                logger.error(f"失败: {item.get('err_msg')}")

        time.sleep(interval)

    return None


def download_and_extract(zip_url: str, output_dir: Path):
    """下载并解压 zip"""
    output_dir.mkdir(parents=True, exist_ok=True)
    import zipfile, io

    resp = requests.get(zip_url, timeout=120)
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        zf.extractall(output_dir)

    logger.info(f"解压到: {output_dir}")
    return output_dir


def run_import(output_dir: Path):
    """运行导入脚本（指定output目录）"""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, str(IMPORT_SCRIPT), str(output_dir)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    # 输出结果到日志
    if result.stdout:
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                logger.info(f"导入: {line}")
    if result.stderr:
        for line in result.stderr.strip().split('\n'):
            if line.strip():
                logger.error(f"导入错误: {line}")

    return result.returncode == 0


def process_pdf_file(pdf_path: str, index: int, total: int):
    """处理单个PDF文件：解析 -> 下载 -> 解压 -> 导入数据库"""
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]

    # 为每个PDF创建独立的output目录
    output_dir = BASE_OUTPUT_DIR / pdf_name
    logger.info(f"\n{'='*60}")
    logger.info(f"处理 PDF [{index}/{total}]: {pdf_name}")
    logger.info(f"输出目录: {output_dir}")
    logger.info(f"{'='*60}")

    # 1. 解析 PDF
    zip_url = create_and_poll_task(pdf_path)
    if not zip_url:
        logger.error(f"PDF处理失败: {pdf_path}")
        return False

    # 2. 下载并解压到独立目录
    download_and_extract(zip_url, output_dir)

    # 3. 导入数据库
    logger.info("开始导入数据库...")
    success = run_import(output_dir)
    if success:
        logger.info(f"PDF [{index}/{total}] 处理完成!")
    else:
        logger.error(f"PDF [{index}/{total}] 导入数据库失败")

    return success


def main():
    logger.info("=" * 60)
    logger.info("MinerU PDF 批量解析 (逐个处理即时导入)")
    logger.info("=" * 60)
    logger.info(f"待处理文件数: {len(PDF_LIST)}")

    for i, pdf_path in enumerate(PDF_LIST, 1):
        if not os.path.exists(pdf_path):
            logger.error(f"\n文件不存在: {pdf_path}")
            continue
        process_pdf_file(pdf_path, i, len(PDF_LIST))

    logger.info(f"\n{'='*60}")
    logger.info("全部处理完成!")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    main()
