"""
WebUI 服务：聊天记录浏览
"""

import json
import logging
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
        # 从静态文件读取 HTML
        static_dir = Path(__file__).parent / "static"
        index_file = static_dir / "index.html"

        if index_file.exists():
            html = index_file.read_text(encoding="utf-8")
        else:
            html = "<h1>404 - index.html not found</h1>"

        return web.Response(text=html, content_type="text/html")

    async def handle_list_chats(self, request):
        """获取聊天列表"""
        chats = []
        data_dir = self.plugin.data_dir

        # 获取筛选参数
        filter_type = request.query.get("type", "all")

        if data_dir.exists():
            for f in data_dir.glob("*.jsonl"):
                # 解析文件名
                parts = f.stem.rsplit("_", 1)
                if len(parts) == 2:
                    chat_id, chat_type = parts
                else:
                    chat_id = f.stem
                    chat_type = "unknown"

                # 应用筛选
                if filter_type != "all" and chat_type != filter_type:
                    continue

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
                        "last_message": (
                            last_msg.get("content", "")[:50] if last_msg else ""
                        ),
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
