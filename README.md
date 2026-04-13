# 汉字字形检索系统

## 目录结构

```
character_search/
├── app/              # 后端 (FastAPI)
├── data/             # 最终数据 (图片 + 数据库)
├── output/           # MinerU 输出目录 (临时)
├── scripts/          # 导入脚本
├── templates/        # 前端 (Vue.js)
├── process_pdf.py    # PDF 处理脚本
└── requirements.txt
```

## 工作流程

```
PDF → MinerU API → output/ → data/ → 前端显示
```

## 1. 处理 PDF 文件

修改 `process_pdf.py` 中的 PDF 路径：

```python
PDF_PATH = r"你的PDF路径\xxx.pdf"
```

运行：
```bash
python process_pdf.py
```

这会：
- 上传 PDF 到 MinerU
- 下载结果到 `output/` 目录
- 解析 458 页（可能需要几分钟）

## 2. 导入数据到数据库

```bash
python scripts/import_content_list.py
```

这会：
- 解析 `output/content_list_v2.json`
- 建立字-图对应关系
- 复制图片到 `data/{汉字}/` 目录
- 导入数据库 `data/characters.db`

当前数据：**714 个汉字，11646 张图片**

## 3. 启动前后端

```bash
cd D:\Microsoft VS Code\lidan\character_search
uvicorn app.main:app --port 8001
```

然后浏览器访问：**http://127.0.0.1:8001**

## 4. 常用操作

### 查看所有汉字
```bash
curl http://127.0.0.1:8001/api/characters
```

### 搜索特定汉字
```bash
curl http://127.0.0.1:8001/api/characters/一
```

### 查看数据库
```bash
sqlite3 data/characters.db "SELECT character, (SELECT COUNT(*) FROM character_images WHERE character_id = characters.id) as cnt FROM characters ORDER BY character;"
```

### 重新导入（会清空旧数据）
```bash
# 1. 删除数据库
del data\characters.db

# 2. 重新导入
python scripts/import_content_list.py
```

## 与 search_web 集成

在 `search_web/app/main.py` 中添加：

```python
from character_search.app.main import app as char_app
app.mount("/char", char_app)
```

访问：**http://127.0.0.1:8000/char**
