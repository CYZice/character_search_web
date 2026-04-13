# 快速打包与部署
# 用法: make build | push | deploy | save | load

IMAGE ?= character_search:latest
REGISTRY ?=

.PHONY: build push deploy save load

# 本地构建镜像
build:
	docker compose build

# 构建并推送到镜像仓库
push: build
	@if [ -z "$(REGISTRY)" ]; then echo "请设置 REGISTRY，如: make push REGISTRY=registry.cn-hangzhou.aliyuncs.com/ns"; exit 1; fi
	docker tag $(IMAGE) $(REGISTRY)/character_search:latest
	docker push $(REGISTRY)/character_search:latest

# 服务器上一键拉取并启动
deploy:
	docker compose pull
	docker compose up -d

# 导出镜像为 tar.gz
save: build
	docker save $(IMAGE) | gzip -c > character_search.tar.gz
	@echo "已生成 character_search.tar.gz，拷到服务器后执行: make load"

# 在服务器上从 tar.gz 加载镜像
load:
	@if [ ! -f character_search.tar.gz ]; then echo "当前目录需要存在 character_search.tar.gz"; exit 1; fi
	gunzip -c character_search.tar.gz | docker load
	@echo "加载完成，执行 docker compose up -d 启动"

# 服务器部署帮助
server-help:
	@echo "--- 服务器首次部署 ---"
	@echo "方式一（tar 包，无需镜像仓库）："
	@echo "  1. 本机: make save"
	@echo "  2. 把 character_search.tar.gz、docker-compose.yml、.env、data/ 等拷到服务器"
	@echo "  3. 服务器: make load && docker compose up -d"
	@echo ""
	@echo "方式二（镜像仓库）："
	@echo "  1. 本机: make push REGISTRY=你的仓库地址"
	@echo "  2. 服务器放好 docker-compose.yml、.env 等"
	@echo "  3. 服务器: make deploy"
