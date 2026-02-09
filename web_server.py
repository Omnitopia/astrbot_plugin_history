"""
WebUI 服务：聊天记录浏览
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from aiohttp import web

logger = logging.getLogger("astrbot")


class WebServer:
    """聊天记录备份 WebUI 服务器"""

    def __init__(self, plugin, host: str = "0.0.0.0", port: int = 8866):
        self.plugin = plugin
        self.host = host
        self.port = port
        self.app = web.Application()
        self.runner = None
        self.site = None
        self._setup_routes()

    def _setup_routes(self):
        """设置路由"""
        self.app.router.add_get("/", self.handle_index)
        self.app.router.add_get("/api/chats", self.handle_list_chats)
        self.app.router.add_get("/api/chat/{filename}", self.handle_get_chat)
        self.app.router.add_get("/api/stats", self.handle_stats)

    async def start(self):
        """启动 Web 服务器"""
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            self.site = web.TCPSite(self.runner, self.host, self.port)
            await self.site.start()
            logger.info(f"📊 聊天记录 WebUI 已启动: http://{self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"❌ WebUI 启动失败: {e}")
            return False

    async def stop(self):
        """停止 Web 服务器"""
        if self.runner:
            await self.runner.cleanup()
            logger.info("📊 聊天记录 WebUI 已停止")

    async def handle_index(self, request):
        """返回首页 HTML"""
        html = self._generate_html()
        return web.Response(text=html, content_type="text/html")

    async def handle_list_chats(self, request):
        """获取聊天列表"""
        chats = []
        data_dir = self.plugin.data_dir

        if data_dir.exists():
            for f in data_dir.glob("*.jsonl"):
                # 解析文件名
                parts = f.stem.rsplit("_", 1)
                if len(parts) == 2:
                    chat_id, chat_type = parts
                else:
                    chat_id = f.stem
                    chat_type = "unknown"

                # 统计消息数
                msg_count = 0
                last_msg = None
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        lines = fp.readlines()
                        msg_count = len(lines)
                        if lines:
                            last_msg = json.loads(lines[-1])
                except Exception:
                    pass

                chats.append(
                    {
                        "filename": f.name,
                        "chat_id": chat_id,
                        "type": chat_type,
                        "message_count": msg_count,
                        "size_kb": round(f.stat().st_size / 1024, 1),
                        "last_message": last_msg.get("content", "")[:50]
                        if last_msg
                        else "",
                        "last_time": last_msg.get("timestamp", "") if last_msg else "",
                    }
                )

        # 按最后消息时间排序
        chats.sort(key=lambda x: x["last_time"], reverse=True)
        return web.json_response(chats)

    async def handle_get_chat(self, request):
        """获取单个聊天的消息"""
        filename = request.match_info["filename"]
        file_path = self.plugin.data_dir / filename

        if not file_path.exists():
            return web.json_response({"error": "Chat not found"}, status=404)

        # 获取分页参数
        page = int(request.query.get("page", 1))
        page_size = int(request.query.get("size", 50))

        messages = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                total = len(lines)

                # 倒序（最新的在前）
                start = max(0, total - page * page_size)
                end = total - (page - 1) * page_size

                for line in lines[start:end]:
                    try:
                        messages.append(json.loads(line.strip()))
                    except Exception:
                        pass

                messages.reverse()

        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

        return web.json_response(
            {"messages": messages, "total": total, "page": page, "page_size": page_size}
        )

    async def handle_stats(self, request):
        """获取统计信息"""
        data_dir = self.plugin.data_dir
        stats = {
            "total_chats": 0,
            "total_messages": 0,
            "total_size_mb": 0,
            "private_chats": 0,
            "group_chats": 0,
        }

        if data_dir.exists():
            for f in data_dir.glob("*.jsonl"):
                stats["total_chats"] += 1
                stats["total_size_mb"] += f.stat().st_size / (1024 * 1024)

                if "_private" in f.name:
                    stats["private_chats"] += 1
                elif "_group" in f.name:
                    stats["group_chats"] += 1

                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        stats["total_messages"] += len(fp.readlines())
                except Exception:
                    pass

        stats["total_size_mb"] = round(stats["total_size_mb"], 2)
        return web.json_response(stats)

    def _generate_html(self):
        """生成首页 HTML"""
        return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🦊 聊天记录备份</title>
    <style>
        :root {
            --primary: #E86A33;
            --primary-light: #F49A6C;
            --bg: #FAF8F5;
            --card-bg: #FFFFFF;
            --text: #3E3832;
            --text-secondary: #8B7E74;
            --border: #E8DED4;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', 'PingFang SC', sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            background: linear-gradient(135deg, var(--primary), var(--primary-light));
            color: white;
            padding: 30px 20px;
            text-align: center;
            border-radius: 16px;
            margin-bottom: 24px;
            box-shadow: 0 4px 20px rgba(232, 106, 51, 0.3);
        }
        
        header h1 {
            font-size: 1.8rem;
            font-weight: 600;
        }
        
        header p {
            opacity: 0.9;
            margin-top: 8px;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        
        .stat-card {
            background: var(--card-bg);
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            border: 1px solid var(--border);
        }
        
        .stat-card .value {
            font-size: 2rem;
            font-weight: 700;
            color: var(--primary);
        }
        
        .stat-card .label {
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-top: 4px;
        }
        
        .chat-list {
            display: grid;
            gap: 12px;
        }
        
        .chat-item {
            background: var(--card-bg);
            padding: 16px 20px;
            border-radius: 12px;
            border: 1px solid var(--border);
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .chat-item:hover {
            border-color: var(--primary);
            box-shadow: 0 2px 12px rgba(232, 106, 51, 0.15);
            transform: translateY(-2px);
        }
        
        .chat-info h3 {
            font-size: 1rem;
            margin-bottom: 4px;
        }
        
        .chat-info .preview {
            color: var(--text-secondary);
            font-size: 0.85rem;
        }
        
        .chat-meta {
            text-align: right;
            font-size: 0.85rem;
            color: var(--text-secondary);
        }
        
        .chat-meta .count {
            color: var(--primary);
            font-weight: 600;
        }
        
        .type-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            margin-left: 8px;
        }
        
        .type-private { background: #E3F2FD; color: #1976D2; }
        .type-group { background: #E8F5E9; color: #388E3C; }
        
        /* 聊天详情模态框 */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
        }
        
        .modal.active { display: flex; align-items: center; justify-content: center; }
        
        .modal-content {
            background: var(--card-bg);
            border-radius: 16px;
            width: 90%;
            max-width: 700px;
            max-height: 80vh;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        
        .modal-header {
            padding: 20px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .modal-header h2 { font-size: 1.2rem; }
        
        .modal-close {
            background: none;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            color: var(--text-secondary);
        }
        
        .modal-body {
            padding: 20px;
            overflow-y: auto;
            flex: 1;
        }
        
        .message {
            margin-bottom: 16px;
            padding: 12px 16px;
            border-radius: 12px;
        }
        
        .message.user {
            background: #E3F2FD;
            margin-left: 40px;
        }
        
        .message.assistant {
            background: #FFF3E0;
            margin-right: 40px;
        }
        
        .message .meta {
            font-size: 0.75rem;
            color: var(--text-secondary);
            margin-bottom: 4px;
        }
        
        .message .content {
            white-space: pre-wrap;
            word-break: break-word;
        }
        
        .load-more {
            text-align: center;
            padding: 16px;
        }
        
        .load-more button {
            background: var(--primary);
            color: white;
            border: none;
            padding: 10px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9rem;
        }
        
        .load-more button:hover {
            background: var(--primary-light);
        }
        
        .empty {
            text-align: center;
            padding: 60px 20px;
            color: var(--text-secondary);
        }
        
        .empty .icon { font-size: 4rem; margin-bottom: 16px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🦊 聊天记录在此！</h1>
            <p>Made with ❤️ by OmniTopia</p>
        </header>
        
        <div class="stats" id="stats"></div>
        
        <div class="chat-list" id="chatList"></div>
    </div>
    
    <div class="modal" id="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="modalTitle">聊天记录</h2>
                <button class="modal-close" onclick="closeModal()">×</button>
            </div>
            <div class="modal-body" id="modalBody"></div>
        </div>
    </div>

    <script>
        let currentChat = null;
        let currentPage = 1;
        
        async function loadStats() {
            const res = await fetch('/api/stats');
            const stats = await res.json();
            document.getElementById('stats').innerHTML = `
                <div class="stat-card">
                    <div class="value">${stats.total_chats}</div>
                    <div class="label">聊天数</div>
                </div>
                <div class="stat-card">
                    <div class="value">${stats.total_messages}</div>
                    <div class="label">消息总数</div>
                </div>
                <div class="stat-card">
                    <div class="value">${stats.private_chats}</div>
                    <div class="label">私聊</div>
                </div>
                <div class="stat-card">
                    <div class="value">${stats.group_chats}</div>
                    <div class="label">群聊</div>
                </div>
                <div class="stat-card">
                    <div class="value">${stats.total_size_mb}</div>
                    <div class="label">存储 (MB)</div>
                </div>
            `;
        }
        
        async function loadChats() {
            const res = await fetch('/api/chats');
            const chats = await res.json();
            const list = document.getElementById('chatList');
            
            if (chats.length === 0) {
                list.innerHTML = `
                    <div class="empty">
                        <div class="icon">📭</div>
                        <p>暂无聊天记录</p>
                        <p>发送消息后这里会显示备份</p>
                    </div>
                `;
                return;
            }
            
            list.innerHTML = chats.map(chat => `
                <div class="chat-item" onclick="openChat('${chat.filename}', '${chat.chat_id}')">
                    <div class="chat-info">
                        <h3>
                            ${chat.chat_id}
                            <span class="type-badge type-${chat.type}">${chat.type === 'private' ? '私聊' : '群聊'}</span>
                        </h3>
                        <div class="preview">${chat.last_message || '暂无消息'}</div>
                    </div>
                    <div class="chat-meta">
                        <div class="count">${chat.message_count} 条消息</div>
                        <div>${chat.size_kb} KB</div>
                    </div>
                </div>
            `).join('');
        }
        
        async function openChat(filename, chatId) {
            currentChat = filename;
            currentPage = 1;
            document.getElementById('modalTitle').textContent = `聊天记录 - ${chatId}`;
            await loadMessages();
            document.getElementById('modal').classList.add('active');
        }
        
        async function loadMessages(append = false) {
            const res = await fetch(`/api/chat/${currentChat}?page=${currentPage}&size=30`);
            const data = await res.json();
            const body = document.getElementById('modalBody');
            
            const html = data.messages.map(msg => `
                <div class="message ${msg.role}">
                    <div class="meta">
                        ${msg.sender_name || msg.role} · ${new Date(msg.timestamp).toLocaleString()}
                    </div>
                    <div class="content">${escapeHtml(msg.content)}</div>
                </div>
            `).join('');
            
            const hasMore = currentPage * 30 < data.total;
            const loadMoreHtml = hasMore ? `
                <div class="load-more">
                    <button onclick="loadMore()">加载更多</button>
                </div>
            ` : '';
            
            if (append) {
                const loadMoreBtn = body.querySelector('.load-more');
                if (loadMoreBtn) loadMoreBtn.remove();
                body.insertAdjacentHTML('beforeend', html + loadMoreHtml);
            } else {
                body.innerHTML = html + loadMoreHtml;
            }
        }
        
        function loadMore() {
            currentPage++;
            loadMessages(true);
        }
        
        function closeModal() {
            document.getElementById('modal').classList.remove('active');
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // 点击模态框外部关闭
        document.getElementById('modal').addEventListener('click', (e) => {
            if (e.target.id === 'modal') closeModal();
        });
        
        // 初始化
        loadStats();
        loadChats();
    </script>
</body>
</html>"""
