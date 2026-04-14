# 快速打包与部署
# 用法: make build | save | upload | deploy | server-help

IMAGE ?= character_search:latest
SERVER ?= root@139.196.90.36
REMOTE_DIR ?= /root/character_search

.PHONY: build save upload upload-data deploy server-help

# 本地构建镜像
build:
	docker build -t $(IMAGE) .

# 打包镜像为 tar.gz
save: build
	docker save $(IMAGE) | gzip -c > character_search.tar.gz
	@echo "已生成 character_search.tar.gz"

# 上传到服务器（需要手动输入密码）
upload: save
	scp character_search.tar.gz docker-compose.yml $(SERVER):$(REMOTE_DIR)/
	@echo "上传完成，在服务器执行: make server-load"

# 上传数据目录到服务器（单独执行）
upload-data:
	rsync -avz --progress data/ $(SERVER):$(REMOTE_DIR)/data/
	@echo "数据上传完成"

# 在服务器上加载镜像
server-load:
	@if [ ! -f character_search.tar.gz ]; then echo "当前目录需要存在 character_search.tar.gz"; exit 1; fi
	gunzip -c character_search.tar.gz | docker load
	@echo "加载完成，执行: docker compose up -d"

# 服务器上一键部署
deploy:
	@echo "=== 服务器部署 ==="
	@echo "1. 本地执行: make upload"
	@echo "2. 服务器执行:"
	@echo "   cd $(REMOTE_DIR)"
	@echo "   gunzip -c character_search.tar.gz | docker load"
	@echo "   docker compose up -d"

# 服务器管理命令（在服务器上执行）
server-help:
	@echo "=== 服务器部署命令 ==="
	@echo ""
	@echo "首次部署:"
	@echo "  mkdir -p $(REMOTE_DIR)"
	@echo "  # 上传镜像和 docker-compose.yml:"
	@echo "  make upload"
	@echo "  # 上传数据（可选，首次必须）:"
	@echo "  make upload-data"
	@echo "  # 服务器执行:"
	@echo "  cd $(REMOTE_DIR)"
	@echo "  gunzip -c character_search.tar.gz | docker load"
	@echo "  docker compose up -d"
	@echo ""
	@echo "日常更新:"
	@echo "  cd $(REMOTE_DIR)"
	@echo "  git pull"
	@echo "  make build && make save"
	@echo "  make upload"
	@echo "  docker compose up -d"
	@echo ""
	@echo "查看日志:"
	@echo "  docker compose logs -f"
	@echo ""
	@echo "同步数据:"
	@echo "  make upload-data"

# 清理
clean:
	rm -f character_search.tar.gz
	docker rmi $(IMAGE) || true
