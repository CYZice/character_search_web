# 汉字字形检索系统

## 项目简介

基于 FastAPI 的汉字字形检索系统，用于辽代汉文石刻文字研究。

## 目录结构

```
character_search/
├── app/              # 后端 (FastAPI)
├── data/             # 数据目录（图片 + SQLite 数据库）
├── output/           # MinerU 输出目录 (临时)
├── scripts/          # 导入脚本
├── templates/        # 前端模板
├── process_pdf.py    # PDF 处理脚本
├── requirements.txt  # Python 依赖
├── Dockerfile        # Docker 镜像构建
├── docker-compose.yml # 容器编排
└── DEPLOY.md         # 部署文档
```

## 本地开发

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
uvicorn app.main:app --port 8001
```

浏览器访问：**http://127.0.0.1:8001**

### 3. API 测试

```bash
# 查看所有汉字
curl http://127.0.0.1:8001/api/characters

# 搜索特定汉字
curl http://127.0.0.1:8001/api/characters/一
```

## Docker 部署

### 服务器信息

| 项目 | 值 |
|------|-----|
| 公网 IP | 139.196.90.36 |
| 私有 IP | 172.24.49.66 |
| SSH 用户 | root |
| 服务端口 | 35827 |

访问地址：**http://139.196.90.36:35827**

### 部署流程

详见 [DEPLOY.md](DEPLOY.md)

#### 快速部署

```bash
# 1. 本地构建并打包
make build
make save

# 2. 上传到服务器
make upload
# 输入密码: f+9WS9t5Bx9&9Xj

# 3. 服务器上加载并启动
ssh root@139.196.90.36
cd /root/character_search
gunzip -c character_search.tar.gz | docker load
docker compose up -d
```

#### 更新部署

```bash
# 服务器上执行
cd /root/character_search
git pull
docker compose up -d --build
```

### 数据同步

```bash
# 同步 data 目录（包含数据库和图片）
rsync -avz --progress data/ root@139.196.90.36:/root/character_search/data/
```

## 工作流程

```
PDF → MinerU API → output/ → data/ → 前端显示
```

### 1. 处理 PDF 文件

修改 `process_pdf.py` 中的 PDF 路径：

```python
PDF_PATH = r"你的PDF路径\xxx.pdf"
```

运行：
```bash
python process_pdf.py
```

### 2. 导入数据到数据库

```bash
python scripts/import_content_list.py
```

这会：
- 解析 `output/content_list_v2.json`
- 建立字-图对应关系
- 复制图片到 `data/{汉字}/` 目录
- 导入数据库 `data/characters.db`

## 数据库查询

```bash
sqlite3 data/characters.db "SELECT character, (SELECT COUNT(*) FROM character_images WHERE character_id = characters.id) as cnt FROM characters ORDER BY character;"
```

## 服务管理

```bash
# 查看日志
docker compose logs -f

# 重启服务
docker compose restart

# 停止服务
docker compose down
```
