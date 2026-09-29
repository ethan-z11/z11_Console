# z11_Console

家庭智能控制台：Vite + React + TypeScript 前端，Python (aiohttp) 后端，可连接 Home Assistant 自动发现房间与设备，支持灯光 / 空调 / 地暖 / 播放器控制、传感器状态摘要、天气、自动化开关、布局拖拽编辑等。

## 安装（Docker，推荐）

需要已安装 Docker 与 Docker Compose。

```bash
git clone https://github.com/<你的用户名>/z11_Console.git
cd z11_Console
cp .env.example .env   # 按需修改端口等配置
docker compose up -d --build
```

启动后访问 `http://<主机>:8765`。

- 默认管理密码：`1234`（进入设置页后请尽快修改）
- 数据保存在 `./data` 目录（账号、布局、加密令牌等），备份整个目录即可
- 修改端口：编辑 `.env` 中的 `HOME_CONSOLE_PORT`，然后 `docker compose up -d`

## 更新

```bash
git pull
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
