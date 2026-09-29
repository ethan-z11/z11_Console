# z11_Console

家庭智能控制台：可连接 Home Assistant 自动发现房间与设备。

## 安装（Docker，推荐）

镜像由 GitHub Actions 自动构建并推送到 ghcr.io，服务器上只需 `docker-compose.yml` 和 `.env` 两个文件（可直接从本目录复制，或用下面命令下载；仓库为私有时 curl 需带 token，直接复制更简单）：

```bash
mkdir z11_Console && cd z11_Console
# 下载 compose 与配置模板（仓库公开时可用）
curl -O https://raw.githubusercontent.com/ethan-z11/z11_Console/main/docker-compose.yml
curl -o .env https://raw.githubusercontent.com/ethan-z11/z11_Console/main/.env.example
# 私有镜像需先登录（Personal Access Token 勾选 read:packages）：
#   echo <TOKEN> | docker login ghcr.io -u ethan-z11 --password-stdin
docker compose pull
docker compose up -d
```

启动后访问 `http://<主机>:8765`。

- 默认管理密码：`1234`（进入设置页后请尽快修改）
- 数据保存在 `./data` 目录（账号、布局、加密令牌等），备份整个目录即可
- 修改端口：编辑 `.env` 中的 `HOME_CONSOLE_PORT`，然后 `docker compose up -d`

## 更新

```bash
docker compose pull
docker compose up -d
```

## 从源码构建

```bash
git clone https://github.com/ethan-z11/z11_Console.git
cd z11_Console
cp .env.example .env
# 编辑 docker-compose.yml：image 一行替换为 build: .（文件内有注释说明）
docker compose up -d --build
```

## 从源码运行（开发）

前端（Vite 会把 `/api` 转发到 `127.0.0.1:8765`）：

```bash
npm install
npm run dev
```

后端：

```bash
cd server
uv sync
uv run python -m home_console_server
```

## 连接 Home Assistant

进入 设置 → 连接，切换数据源为 Home Assistant，填写 HA 地址与长期访问令牌即可，服务会自动发现房间与设备。

## 常见问题

- **构建时拉取基础镜像失败**：部分网络环境无法访问 docker.io，可改用 AWS ECR 公共镜像，见 `docker-compose.yml` 中的注释。
- **被 Home Assistant 以 iframe 嵌入**：跨站时需要 HTTPS 并把 `.env` 中 `HOME_CONSOLE_COOKIE_SAMESITE` 设为 `None`。

# AI全程制作，作者仅指导AII。
