# Claude History

Claude Code 对话历史可视化管理工具。用浏览器查看、搜索、管理你的所有 Claude Code 对话记录。


## 功能

- 📋 浏览所有历史对话，按日期分组
- 🔍 实时搜索对话内容
- 🏷️ 自动打标签分类（产品设计、代码开发等）
- 🧠 调用 Claude API 自动生成对话标题（缓存到本地，不重复调用）
- 📊 显示每个会话的 token 消耗（输入/缓存/输出）
- 🗑️ 一键将对话移到回收站
- ▶️ 点击按钮在终端里恢复对话（`claude --resume`）

## 环境要求

- macOS
- Python 3.9+
- Claude Code 已安装（`~/.claude/` 目录存在）

## 安装

```bash
git clone https://github.com/your-username/claude-history.git
cd claude-history
```

不需要安装任何依赖，只用 Python 标准库。

## 使用

```bash
python3 server.py
```

然后浏览器打开 [http://localhost:8765](http://localhost:8765)

### 可选：桌面快捷方式（macOS）

在桌面创建 `Claude History.command` 文件，内容如下：

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

## AI 标题生成（可选）

工具会自动调用 Claude API 为每个对话生成标题，结果缓存到 `titles.json`，不重复调用。

需要在 `~/.claude/settings.json` 里配置 API Key（Claude Code 用户通常已配置好）：

```json
{
  "env": {
    "ANTHROPIC_API_KEY": "sk-...",
    "ANTHROPIC_BASE_URL": "https://api.anthropic.com"
  }
}
```

若无 API Key，工具仍可正常使用，只是标题会显示对话的第一句话。

## 文件说明

```
claude-history/
  server.py     # Python 后端服务器
  index.html    # 前端页面
  README.md     # 本文件
```

`titles.json` 和 `sessions_cache.json` 会在首次运行时自动生成，无需手动创建。

## 注意事项

- 删除操作会将文件移入 macOS 回收站，不会直接删除
- 服务器只监听本地 localhost，不会暴露到外网
- 对话数据完全在本地，不会上传到任何服务器（除 AI 标题生成时发送摘要到 Claude API）
