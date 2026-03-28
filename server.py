#!/usr/bin/env python3
"""
Claude 对话历史管理服务器
启动: python3 server.py
访问: http://localhost:8765
"""

import json
import os
import re
import subprocess
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse, unquote

PORT = 8765
STATIC_DIR = Path(__file__).parent

# 自动扫描 ~/.claude/projects/ 下所有含 jsonl 的目录
def find_sessions_dirs() -> list:
    base = Path.home() / ".claude/projects"
    if not base.exists():
        return []
    dirs = []
    for d in base.iterdir():
        if d.is_dir() and any(d.glob("*.jsonl")):
            dirs.append(d)
    return dirs

SESSIONS_DIRS = find_sessions_dirs()
TITLES_CACHE   = STATIC_DIR / "titles.json"
SESSIONS_CACHE = STATIC_DIR / "sessions_cache.json"

# ── 读取 Claude Code 配置的 API 信息 ────────────────
def load_api_config():
    settings = Path.home() / ".claude/settings.json"
    try:
        d = json.loads(settings.read_text())
        env = d.get('env', {})
        return {
            'api_key': env.get('ANTHROPIC_API_KEY', ''),
            'base_url': env.get('ANTHROPIC_BASE_URL', 'https://api.anthropic.com').rstrip('/'),
            'haiku': env.get('ANTHROPIC_DEFAULT_HAIKU_MODEL', 'claude-haiku-4-5-20251001'),
        }
    except Exception:
        return {'api_key': '', 'base_url': 'https://api.anthropic.com', 'haiku': 'claude-haiku-4-5-20251001'}

API_CFG = load_api_config()

# ── 标题缓存 ─────────────────────────────────────────
def load_titles_cache():
    try:
        return json.loads(TITLES_CACHE.read_text())
    except Exception:
        return {}

def save_titles_cache(cache):
    TITLES_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2))

# ── AI 生成标题 ──────────────────────────────────────
def generate_title(uuid: str, summary: str, first_message: str) -> str:
    if not API_CFG['api_key']:
        return ''
    prompt = f"""请用 10 字以内的中文为以下对话起一个简洁的标题，直接输出标题文字，不要引号、不要标点、不要解释。

对话开头：{first_message[:100]}
对话摘要：{summary[:200]}"""

    payload = json.dumps({
        "model": API_CFG['haiku'],
        "max_tokens": 50,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()

    req = urllib.request.Request(
        f"{API_CFG['base_url']}/v1/messages",
        data=payload,
        headers={
            "x-api-key": API_CFG['api_key'],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data['content'][0]['text'].strip()
    except Exception as e:
        print(f"Title gen error: {e}")
        return ''

# ── 标签规则 ─────────────────────────────────────────
TAG_RULES = [
    ("IoT 协议",   ["matter", "zigbee", "蓝牙", "wifi", "thread", "协议", "ble", "mesh"]),
    ("米家产品",   ["米家", "miot", "物模型", "品类", "接入", "小米"]),
    ("照明电工",   ["照明", "开关", "灯", "色温", "亮度", "调光", "插座", "电工"]),
    ("AI 工具",    ["claude", "gpt", "llm", "ai", "模型", "prompt", "skill", "agent"]),
    ("代码开发",   ["代码", "bug", "api", "接口", "开发", "部署", "测试", "python", "js", "curl"]),
    ("产品设计",   ["产品", "需求", "功能", "规范", "文档", "prd", "用户", "体验"]),
    ("工具配置",   ["mcp", "飞书", "vscode", "terminal", "setting", "配置", "安装", "插件"]),
    ("传感器",     ["传感器", "sensor", "存在", "温度", "湿度", "检测", "识别"]),
    ("职业发展",   ["简历", "求职", "面试", "岗位", "机器人", "具身", "转型", "职业"]),
    ("市场调研",   ["竞品", "市场", "调研", "平台", "品牌", "淘宝", "行业"]),
    ("写作文档",   ["总结", "整理", "写作", "翻译", "文章", "报告", "会议"]),
    ("生活杂谈",   ["生活", "旅行", "美食", "朋友", "家人", "电影", "音乐", "周末"]),
]

def auto_tags(text: str) -> list:
    text_lower = text.lower()
    scores = [(sum(1 for kw in kws if kw in text_lower), tag)
              for tag, kws in TAG_RULES]
    scores = [(s, t) for s, t in scores if s > 0]
    scores.sort(reverse=True)
    return [t for _, t in scores[:3]] or ["其他"]

# ── 文本清洗 ─────────────────────────────────────────
def clean_text(text: str) -> str:
    text = re.sub(r'<[^>]+>.*?</[^>]+>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+/>', '', text)
    return text.strip()

def extract_user_text(content) -> str:
    if isinstance(content, str):
        t = clean_text(content)
        return t if not t.startswith('<') else ''
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get('type') == 'text':
                t = clean_text(item.get('text', ''))
                if t and not t.startswith('<'):
                    return t
    return ''

# ── 解析单个会话 ─────────────────────────────────────
def parse_session(filepath: Path, titles_cache: dict):
    try:
        uuid = None
        first_message = ''
        summary_parts = []
        model = ''
        message_count = 0
        timestamp = None
        total_input_tokens = 0
        total_output_tokens = 0
        total_cache_tokens = 0

        name = filepath.stem
        uuid_pattern = r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$'
        m = re.search(uuid_pattern, name)
        if m:
            uuid = m.group(1)
            first_message = name[:m.start()].rstrip('_').strip()
        else:
            uuid = name[-36:] if len(name) >= 36 else name
            first_message = name

        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                rtype = record.get('type', '')
                if not timestamp and record.get('timestamp'):
                    timestamp = record['timestamp']

                if rtype == 'user':
                    message_count += 1
                    content = record.get('message', {}).get('content', '')
                    text = extract_user_text(content)
                    if text and len(summary_parts) < 3:
                        summary_parts.append(text[:100])

                elif rtype == 'assistant':
                    message_count += 1
                    msg = record.get('message', {})
                    if not model:
                        model = msg.get('model', '')
                    usage = msg.get('usage', {})
                    total_input_tokens  += usage.get('input_tokens', 0)
                    total_output_tokens += usage.get('output_tokens', 0)
                    total_cache_tokens  += usage.get('cache_read_input_tokens', 0)

        if not uuid:
            return None

        summary = ' / '.join(summary_parts)[:200]
        tags = auto_tags(first_message + ' ' + summary)

        # 时间解析
        date_str, time_str = '', ''
        if timestamp:
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                local_dt = dt.astimezone()
                date_str = local_dt.strftime('%Y-%m-%d')
                time_str = local_dt.strftime('%H:%M')
            except Exception:
                pass

        model_short = model.split('/')[-1] if '/' in model else model

        # 标题：优先用缓存
        title = titles_cache.get(uuid, '')

        return {
            'uuid': uuid,
            'filename': filepath.name,
            'date': date_str,
            'time': time_str,
            'first_message': first_message,
            'title': title,
            'summary': summary,
            'model': model_short,
            'tags': tags,
            'message_count': message_count,
            'tokens': {
                'input': total_input_tokens,
                'output': total_output_tokens,
                'cache': total_cache_tokens,
                'total': total_input_tokens + total_output_tokens + total_cache_tokens,
            }
        }
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return None


def load_sessions_cache():
    try:
        return json.loads(SESSIONS_CACHE.read_text())
    except Exception:
        return {}

def save_sessions_cache(cache: dict):
    SESSIONS_CACHE.write_text(json.dumps(cache, ensure_ascii=False))

def get_sessions() -> list:
    titles_cache = load_titles_cache()
    sessions_cache = load_sessions_cache()
    sessions = []
    updated = False

    if not SESSIONS_DIRS:
        return sessions

    all_files = [f for d in SESSIONS_DIRS for f in d.glob('*.jsonl')]
    for f in all_files:
        mtime = str(f.stat().st_mtime)
        cached = sessions_cache.get(f.name)
        if cached and cached.get('_mtime') == mtime:
            # 缓存命中，直接用，但更新 title
            s = cached.copy()
            uuid = s.get('uuid', '')
            if uuid and titles_cache.get(uuid):
                s['title'] = titles_cache[uuid]
            sessions.append(s)
        else:
            # 需要重新解析
            s = parse_session(f, titles_cache)
            if s:
                s['_mtime'] = mtime
                sessions_cache[f.name] = s
                sessions.append(s)
                updated = True

    # 清理缓存中已不存在的文件
    existing = {f.name for d in SESSIONS_DIRS for f in d.glob('*.jsonl')}
    stale = [k for k in sessions_cache if k not in existing]
    if stale:
        for k in stale:
            del sessions_cache[k]
        updated = True

    if updated:
        save_sessions_cache(sessions_cache)

    sessions.sort(key=lambda x: (x.get('date',''), x.get('time','')), reverse=True)
    return sessions


def get_messages(uuid: str) -> list:
    filepath = None
    for d in SESSIONS_DIRS:
        for f in d.glob('*.jsonl'):
            if uuid in f.name:
                filepath = f
                break
        if filepath:
            break
    if not filepath:
        return []

    messages = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            rtype = record.get('type', '')
            if rtype not in ('user', 'assistant'):
                continue

            content = record.get('message', {}).get('content', '')
            text = ''
            if rtype == 'user':
                text = extract_user_text(content)
            else:
                if isinstance(content, list):
                    parts = [item.get('text', '') for item in content
                             if isinstance(item, dict) and item.get('type') == 'text']
                    text = '\n'.join(parts)
                elif isinstance(content, str):
                    text = content

            if text.strip():
                messages.append({
                    'role': rtype,
                    'text': text.strip(),
                    'timestamp': record.get('timestamp', ''),
                })
    return messages


def open_terminal(uuid: str) -> bool:
    script = f'''
        tell application "Terminal"
            activate
            do script "claude --resume {uuid}"
        end tell
    '''
    try:
        subprocess.run(['osascript', '-e', script], check=True)
        return True
    except Exception as e:
        print(f"Error opening Terminal: {e}")
        return False


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[{self.address_string()}] {format % args}")

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, filepath: Path):
        try:
            content = filepath.read_bytes()
            mime = {'.html': 'text/html; charset=utf-8', '.js': 'application/javascript', '.css': 'text/css'}.get(filepath.suffix, 'application/octet-stream')
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path == '/api/sessions':
            self.send_json(get_sessions())
        elif path.startswith('/api/session/') and path.endswith('/messages'):
            uuid = path[len('/api/session/'):-len('/messages')]
            self.send_json(get_messages(uuid))
        elif path == '/' or path == '/index.html':
            self.send_file(STATIC_DIR / 'index.html')
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        if path == '/api/open-vscode':
            ok = open_terminal(body.get('uuid', ''))
            self.send_json({'ok': ok})

        elif path == '/api/generate-title':
            uuid = body.get('uuid', '')
            summary = body.get('summary', '')
            first_message = body.get('first_message', '')
            title = generate_title(uuid, summary, first_message)
            if title:
                cache = load_titles_cache()
                cache[uuid] = title
                save_titles_cache(cache)
                # 同步到 sessions_cache
                sc = load_sessions_cache()
                for v in sc.values():
                    if isinstance(v, dict) and v.get('uuid') == uuid:
                        v['title'] = title
                save_sessions_cache(sc)
            self.send_json({'title': title})

        else:
            self.send_response(404)
            self.end_headers()

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path.startswith('/api/session/'):
            uuid = path[len('/api/session/'):]
            if not re.match(r'^[0-9a-f-]{36}$', uuid):
                self.send_json({'ok': False, 'error': 'invalid uuid'}, 400)
                return
            deleted = False
            for d in SESSIONS_DIRS:
                for f in d.glob('*.jsonl'):
                    if uuid in f.name:
                        subprocess.run(['osascript', '-e',
                            f'tell application "Finder" to delete POSIX file "{f}"'], check=True)
                        deleted = True
                        break
                if deleted:
                    break
            # 同时删除标题缓存
            if deleted:
                cache = load_titles_cache()
                cache.pop(uuid, None)
                save_titles_cache(cache)
            self.send_json({'ok': deleted, 'error': None if deleted else 'file not found'})
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == '__main__':
    server = HTTPServer(('localhost', PORT), Handler)
    print(f"Claude 对话历史管理器")
    print(f"访问: http://localhost:{PORT}")
    print(f"数据目录: {[str(d) for d in SESSIONS_DIRS]}")
    print(f"API: {API_CFG['base_url']} / {API_CFG['haiku']}")
    print(f"按 Ctrl+C 停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
