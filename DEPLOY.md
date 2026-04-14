# 部署文档

## 服务器信息

| 项目 | 值 |
|------|-----|
| 公网 IP | 139.196.90.36 |
| 私有 IP | 172.24.49.66 |
| SSH 端口 | 22 |
| 用户 | root |
| 密码 | `f+9WS9t5Bx9&9Xj` |

## 服务地址

- **端口**: 35827
- **访问**: http://139.196.90.36:35827

## 目录结构

服务器上使用统一的项目目录：

```
/root/character_search/     # 项目根目录
├── app/                   # 应用代码
├── data/                  # 数据目录（图片 + SQLite 数据库）
├── templates/             # 前端模板
├── docker-compose.yml     # 容器编排配置
└── .env                   # 环境变量（敏感信息）
```

## 部署方式

### 方式一：tar 包部署（推荐，无需镜像仓库）

#### 1. 本地构建并打包

```bash
cd D:\Microsoft VS Code\lidan\character_search

# 构建镜像
docker build -t character_search:latest .

# 打包
docker save character_search:latest | gzip > character_search.tar.gz
```

#### 2. 上传到服务器

```bash
scp character_search.tar.gz docker-compose.yml root@139.196.90.36:/root/character_search/
```

> 注意：首次部署需要先在服务器上创建目录：
> ```bash
> ssh root@139.196.90.36 "mkdir -p /root/character_search"
> ```

#### 3. 服务器上加载镜像

```bash
ssh root@139.196.90.36
```

密码：`f+9WS9t5Bx9&9Xj`

```bash
cd /root/character_search
gunzip -c character_search.tar.gz | docker load
```

#### 4. 启动服务

```bash
docker compose up -d
```

#### 5. 验证

```bash
curl http://localhost:35827
```

---

### 方式二：镜像仓库

#### 1. 构建并推送

```bash
make push REGISTRY=registry.cn-hangzhou.aliyuncs.com/你的命名空间
```

#### 2. 服务器拉取启动

```bash
ssh root@139.196.90.36
cd /root/character_search_web
docker compose pull
docker compose up -d
```

---

## 数据同步

### 同步 data 目录（重要）

项目依赖 `data/` 目录，包含：
- `characters.db` - SQLite 数据库
- 汉字图片文件

```bash
# 在有数据的机器上执行
rsync -avz --progress data/ root@139.196.90.36:/root/character_search/data/
```

---

## 服务管理

```bash
# 查看日志
cd /root/character_search && docker compose logs -f

# 查看状态
docker compose ps

# 重启服务
cd /root/character_search && docker compose restart

# 停止服务
cd /root/character_search && docker compose down

# 更新部署（从 git）
git pull
docker compose up -d --build
```

---

## 服务器要求

- Docker 已安装
- 端口 35827 已开放（防火墙）
- data 目录已同步（包含 characters.db 和图片）

---

## 快速部署脚本

在服务器上创建 `deploy.sh` 方便日常部署：

```bash
#!/bin/bash
# /root/character_search/deploy.sh

set -e

cd /root/character_search

echo "=== 拉取最新代码 ==="
git pull

echo "=== 同步 data 目录 ==="
# 如果有本地数据需要同步
# rsync -avz --progress data/ root@139.196.90.36:/root/character_search/data/

echo "=== 构建并启动 ==="
docker compose up -d --build

echo "=== 检查状态 ==="
docker compose ps
curl -s http://localhost:35827 > /dev/null && echo "服务正常" || echo "服务异常"
```
