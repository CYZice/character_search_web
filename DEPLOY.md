# Docker 部署文档

## 部署方式

### 方式一：tar 包部署（无需镜像仓库）

#### 1. 构建镜像

```bash
git clone https://github.com/CYZice/character_search_web.git
cd character_search_web
make build
```

#### 2. 打包

```bash
make save
```

会生成 `character_search.tar.gz`

#### 3. 上传到服务器

```bash
scp character_search.tar.gz root@139.196.90.36:~/
```

#### 4. 服务器上加载镜像

```bash
ssh root@139.196.90.36
gunzip -c character_search.tar.gz | docker load
```

#### 5. 启动服务

```bash
docker compose up -d
```

#### 6. 验证

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
docker compose pull
docker compose up -d
```

---

## 同步数据（重要）

项目依赖 `data/` 目录（包含 SQLite 数据库和汉字图片）。部署时需要同步：

```bash
# 在有数据的机器上
rsync -avz --progress data/ root@139.196.90.36:~/character_search_web/data/
```

---

## 服务地址

- **端口**: 35827
- **访问**: http://139.196.90.36:35827

---

## 常用命令

```bash
# 查看日志
docker compose logs -f

# 重启服务
docker compose restart

# 停止服务
docker compose down

# 更新重启
git pull && docker compose up -d --build
```

---

## 服务器要求

- Docker 已安装
- 端口 35827 已开放（防火墙）
- data 目录已同步（包含 characters.db 和图片）
