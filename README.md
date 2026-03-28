# Claude History

A local web app to browse, search, and **resume** your Claude Code conversation history — pick up any past conversation right where you left off.

一个本地 Web 工具，用于浏览、搜索和**继续**你的 Claude Code 对话历史 —— 随时找到并接续任意一个历史会话。

![screenshot](screenshot.png)

---

## English

### Features

- 📋 Browse all past conversations, grouped by date
- 🔍 Real-time search across conversation content
- 🏷️ Auto-tagging by topic (IoT, Product Design, Coding, etc.)
- 🧠 AI-generated titles via Claude API (cached locally, no repeated calls)
- 📊 Token usage stats per session (input / cache / output)
- 🗑️ Move conversations to Trash with one click
- ▶️ Resume any conversation in terminal with `claude --resume`

### Requirements

- macOS
- Python 3.9+
- Claude Code installed (`~/.claude/` directory exists)

### Installation

```bash
git clone https://github.com/kary724/claude-history.git
cd claude-history
```

No dependencies required — uses Python standard library only.

### Usage

```bash
python3 server.py
```

Open [http://localhost:8765](http://localhost:8765) in your browser.

### macOS Quick Launch (optional)

Create `Claude History.command` on your Desktop:

```bash
#!/bin/zsh
lsof -ti:8765 | xargs kill -9 2>/dev/null
nohup python3 /path/to/claude-history/server.py > /tmp/claude-history.log 2>&1 &
sleep 1.5
open http://localhost:8765
exit
```

```bash
chmod +x ~/Desktop/Claude\ History.command
```

### AI Title Generation (optional)

Requires an API key in `~/.claude/settings.json` (already set up if you use Claude Code):

```json
{
  "env": {
    "ANTHROPIC_API_KEY": "sk-...",
    "ANTHROPIC_BASE_URL": "https://api.anthropic.com"
  }
}
```

Without an API key, titles fall back to the first message of each conversation.

---

## 中文说明

### 功能

- 📋 浏览所有历史对话，按日期分组
- 🔍 实时搜索对话内容
- 🏷️ 自动按主题打标签（IoT协议、产品设计、代码开发等）
- 🧠 调用 Claude API 自动生成对话标题（结果缓存到本地，不重复调用）
- 📊 显示每个会话的 token 消耗（输入 / 缓存 / 输出）
- 🗑️ 一键将对话移到回收站
- ▶️ 点击按钮在终端里通过 `claude --resume` 继续对话

### 环境要求

- macOS
- Python 3.9+
- 已安装 Claude Code（`~/.claude/` 目录存在）

### 安装

```bash
git clone https://github.com/kary724/claude-history.git
cd claude-history
```

无需安装任何依赖，只使用 Python 标准库。

### 使用

```bash
python3 server.py
```

然后浏览器打开 [http://localhost:8765](http://localhost:8765)。

### macOS 桌面快捷方式（可选）

在桌面创建 `Claude History.command` 文件，内容：

```bash
#!/bin/zsh
lsof -ti:8765 | xargs kill -9 2>/dev/null
nohup python3 /path/to/claude-history/server.py > /tmp/claude-history.log 2>&1 &
sleep 1.5
open http://localhost:8765
exit
```

```bash
chmod +x ~/Desktop/Claude\ History.command
```

双击即可启动。

### AI 标题生成（可选）

需要在 `~/.claude/settings.json` 里配置 API Key（Claude Code 用户通常已自动配置好）：

```json
{
  "env": {
    "ANTHROPIC_API_KEY": "sk-...",
    "ANTHROPIC_BASE_URL": "https://api.anthropic.com"
  }
}
```

没有 API Key 时工具仍可正常使用，标题会显示每个对话的第一句话。

---

## Notes / 说明

- 删除操作将文件移入 macOS 回收站，不会直接删除 / Deleted conversations are moved to Trash, not permanently deleted
- 服务器只监听本地 localhost，不会暴露到外网 / Server only listens on localhost
- 对话数据完全在本地，AI 标题生成时仅发送摘要到 Claude API / All data stays local
