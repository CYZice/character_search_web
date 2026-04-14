# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

辽代汉文石刻文字研究 - 汉字字形检索系统。

## 项目结构

```
character_search/
├── app/              # FastAPI 后端
├── data/             # 数据（SQLite 数据库 + 汉字图片）
├── output/           # MinerU 处理结果临时目录
├── scripts/          # 数据导入脚本
├── templates/        # 前端模板
├── Dockerfile        # Docker 镜像构建
├── docker-compose.yml # 容器编排
├── Makefile          # 部署命令
├── DEPLOY.md         # 部署文档
└── README.md         # 项目文档
```

## 部署相关

### 服务器信息

- 公网 IP: 139.196.90.36
- 私有 IP: 172.24.49.66
- 用户: root
- 密码: `f+9WS9t5Bx9&9Xj`
- 服务端口: 35827

### 部署命令

```bash
# 本地构建打包
make build
make save

# 上传到服务器
make upload

# 服务器加载启动
ssh root@139.196.90.36
cd /root/character_search
gunzip -c character_search.tar.gz | docker load
docker compose up -d
```

### 数据同步

```bash
rsync -avz --progress data/ root@139.196.90.36:/root/character_search/data/
```

## 工作流程

```
PDF → MinerU API → output/ → data/ → 前端显示
```

## PDF 格式

目标 PDFs 采用**双栏布局**：
- 每栏以【】包围的汉字标题开头
- 随后是该汉字的垂直堆叠图片
- 阅读顺序：左栏从上到下，然后右栏

## MinerU API

- v1 API: `https://mineru.net/api/v1/agent`
- v4 API: `https://mineru.net/api/v4`

## 主要脚本

| 文件 | 用途 |
|------|------|
| `process_pdf.py` | 单个 PDF 处理 |
| `process_pdfs_batch.py` | 批量 PDF 处理 |
| `scripts/import_content_list.py` | 数据导入数据库 |

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| IMAGE_NAME | character_search:latest | Docker 镜像名 |
| DATABASE_URL | sqlite:///./data/characters.db | 数据库连接 |
| LOG_LEVEL | INFO | 日志级别 |
