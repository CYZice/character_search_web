"""
MinerU 精准解析 API - 处理PDF并提取字与图片对应
"""
import requests
import time
import os
import json
import zipfile
import io
from pathlib import Path

# ========== 配置 ==========
PDF_PATH = r"C:\Users\Lenovo\Downloads\遼代漢文石刻文字研究_程玲玲-part0.pdf"
OUTPUT_DIR = Path(r"D:\Microsoft VS Code\lidan\character_search\output")

TOKEN = "eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFM1MTIifQ.eyJqdGkiOiI3NDEwMDY5MiIsInJvbCI6IlJPTEVfUkVHSVNURVIiLCJpc3MiOiJPcGVuWExhYiIsImlhdCI6MTc3NTcyODg3NCwiY2xpZW50SWQiOiJsa3pkeDU3bnZ5MjJqa3BxOXgydyIsInBob25lIjoiIiwib3BlbklkIjpudWxsLCJ1dWlkIjoiZmRjZDZhYTEtY2M5Ni00NzI1LWE4YWItMmNiNzRkZTQ4ODljIiwiZW1haWwiOiIiLCJleHAiOjE3ODM1MDQ4NzR9.qAjuXVV73cCmIb5OyGhKiCMMonE1rSIOFKafUTPaqOlx2sxyAViTK25e39NZ5tCD7oKY9rBkvO76msIM6UiJIQ"
BASE_URL = "https://mineru.net/api/v4"
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"}
# ========== 配置 ==========


def create_and_poll_task(file_path: str):
    """创建任务并轮询结果"""
    file_name = os.path.basename(file_path)

    # 1. 申请上传链接
    url = f"{BASE_URL}/file-urls/batch"
    data = {"files": [{"name": file_name, "data_id": "pdf_char"}], "model_version": "vlm"}

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


def main():
    print("=" * 60)
    print("MinerU PDF 解析")
    print("=" * 60)

    # 1. 解析 PDF
    zip_url = create_and_poll_task(PDF_PATH)
    if not zip_url:
        return

    # 2. 下载解压
    download_and_extract(zip_url, OUTPUT_DIR)

    print("\n解析完成! 输出目录:", OUTPUT_DIR)
    print("\n接下来运行导入脚本:")
    print(f"  python scripts/import_content_list.py")


if __name__ == "__main__":
    main()
