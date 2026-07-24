# 企业微信智能机器人 — 部署文档

---

## 1. 环境要求

| 项 | 要求 |
|---|------|
| Python | ≥ 3.8 |
| 操作系统 | Windows / Linux / macOS |
| 网络 | 能访问 `wss://openws.work.weixin.qq.com` |

---

## 2. 获取配置

1. 登录[企业微信后台](https://work.weixin.qq.com/)
2. 进入「应用管理」→「智能机器人」→「API 配置」
3. 获取 **Bot ID** 和 **Secret**
4. 填入 `.env` 文件中：

```bash
WECOM_BOT_ID=aib_xxxxxxxxxxxxx
WECOM_BOT_SECRET=xxxxxxxxxxxxxxxx
```

---

## 3. 快速部署（开发/测试）

```bash
# 克隆或进入项目目录
cd wexbot

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动机器人
python main.py
```

---

## 4. 生产环境部署

### 4.1 使用 systemd（Linux 推荐）

创建服务文件 `/etc/systemd/system/wexbot.service`：

```ini
[Unit]
Description=企业微信智能机器人
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/wexbot
Environment="PATH=/opt/wexbot/venv/bin"
ExecStart=/opt/wexbot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 部署步骤
sudo mkdir -p /opt/wexbot
sudo cp -r . /opt/wexbot/
cd /opt/wexbot
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# 启动服务
sudo systemctl daemon-reload
sudo systemctl enable wexbot
sudo systemctl start wexbot

# 查看日志
sudo journalctl -u wexbot -f
```

### 4.2 使用 Supervisor（Linux/macOS）

安装 Supervisor：

```bash
pip install supervisor
```

创建配置 `/etc/supervisor/conf.d/wexbot.conf`：

```ini
[program:wexbot]
directory=/opt/wexbot
command=/opt/wexbot/venv/bin/python main.py
autostart=true
autorestart=true
startsecs=10
stdout_logfile=/var/log/wexbot/out.log
stderr_logfile=/var/log/wexbot/err.log
user=www-data
```

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start wexbot
```

### 4.3 使用 Docker

创建 `Dockerfile`：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

构建并运行：

```bash
# 构建镜像
docker build -t wexbot .

# 运行容器
docker run -d \
  --name wexbot \
  --restart=always \
  --env-file .env \
  wexbot
```

使用 `docker-compose.yml`：

```yaml
version: "3.8"

services:
  wexbot:
    build: .
    container_name: wexbot
    restart: always
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
```

```bash
docker compose up -d
```

### 4.4 Windows 部署（后台运行）

使用 **NSSM（Non-Sucking Service Manager）** 注册为 Windows 服务：

```powershell
# 下载 NSSM: https://nssm.cc/download

# 注册服务
nssm install wexbot

# 在 GUI 中配置：
#   Application Path: C:\path\to\venv\Scripts\python.exe
#   Startup Dir:       C:\path\to\wexbot
#   Arguments:         main.py

# 启动服务
nssm start wexbot
```

---

## 5. 配置参考

`.env` 完整配置项：

```bash
# ========== 必填 ==========
WECOM_BOT_ID=aib_xxxxxxxxxxxxx          # Bot ID
WECOM_BOT_SECRET=xxxxxxxxxxxxxxxx        # Secret 密钥

# ========== 可选 ==========
WECOM_WS_URL=                            # 自定义 WebSocket（留空用官方）
WECOM_HEARTBEAT_INTERVAL=30000           # 心跳间隔（毫秒）
WECOM_RECONNECT_INTERVAL=1000            # 重连延迟（毫秒）
WECOM_MAX_RECONNECT_ATTEMPTS=10          # 最大重连次数（-1=无限）

# ========== 行为配置 ==========
ENABLE_STREAM_REPLY=true                 # 流式回复开关
STREAM_THINKING_TEXT=正在思考中...        # 流式回复提示语
WELCOME_TEXT=您好！我是智能助手...        # 进入会话欢迎语
ENABLE_COMMANDS=true                     # 命令系统开关
ENABLE_AI_REPLY=false                    # AI 回复开关（需自行对接）
```

---

## 6. 运行状态检查

### 健康检查

```bash
# 进程存在性
ps aux | grep main.py        # Linux/macOS
tasklist | findstr python    # Windows

# 查看实时日志（无额外配置时输出到 stdout）
sudo journalctl -u wexbot -f
```

### 企业微信侧验证

向机器人发送 `/ping`，收到 `🏓 pong! 机器人在线运行中` 即表示部署成功。

---

## 7. 日志

默认输出到标准输出（stdout）。如需文件日志，可在 `main.py` 中挂载自定义 Logger：

```python
from aibot import WSClient, WSClientOptions, DefaultLogger
import logging

# 自定义 log 文件
fh = logging.FileHandler("wexbot.log", encoding="utf-8")
fh.setLevel(logging.INFO)

class FileLogger:
    def debug(self, msg, *args): logging.debug(msg, *args)
    def info(self, msg, *args): logging.info(msg, *args)
    def warn(self, msg, *args): logging.warning(msg, *args)
    def error(self, msg, *args): logging.error(msg, *args)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[fh, logging.StreamHandler()],
)

ws_client = WSClient(
    WSClientOptions(
        bot_id="...",
        secret="...",
        logger=FileLogger(),
    )
)
```

---

## 8. 常见问题

### Q: 连接失败
- 确认服务器能访问外网 WebSocket（`wss://openws.work.weixin.qq.com`）
- 检查 `.env` 中 Bot ID 和 Secret 是否正确
- 查看是否有防火墙/代理拦截

### Q: 认证失败
- Bot ID 或 Secret 有误
- 检查企业微信后台是否已启用该机器人

### Q: 断线频繁
- 增大 `WECOM_HEARTBEAT_INTERVAL`
- 增大 `WECOM_MAX_RECONNECT_ATTEMPTS`（或设为 -1 无限重连）
- 检查网络稳定性

### Q: 欢迎语未发送
- `event.enter_chat` 必须 **5 秒内** 调用 `reply_welcome`，超时会失败
- 生产环境请确保无阻塞操作在进入会话事件中

---

## 9. 扩展：对接 AI 服务

将 `ENABLE_AI_REPLY=true`，然后在 `main.py` 的 `on_text` 处理中接入外部 AI API：

```python
import aiohttp

async def call_ai_api(prompt: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://your-ai-api.com/chat",
            json={"messages": [{"role": "user", "content": prompt}]},
            headers={"Authorization": "Bearer YOUR_KEY"},
        ) as resp:
            data = await resp.json()
            return data["choices"][0]["message"]["content"]
```

在 `on_text` 中调用该函数替换默认回复即可。
