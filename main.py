"""
AstrBot Plugin: 聊天记录备份
============================
实时备份聊天记录，防止对话历史丢失。

作者: OmniTopia (https://github.com/OmniTopia)
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from astrbot.api import logger, AstrBotConfig
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.event.filter import EventMessageType, PlatformAdapterType
from astrbot.api.star import Context, Star


class Main(Star):
    """聊天记录备份插件"""
    
    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        self.config = config or {}
        
        # 获取插件数据目录
        plugin_name = getattr(self, "name", "astrbot_plugin_history")
        try:
            from astrbot.core.utils.astrbot_path import get_astrbot_data_path
            self.data_dir = Path(get_astrbot_data_path()) / "plugin_data" / plugin_name
        except ImportError:
            self.data_dir = Path("data") / "plugin_data" / plugin_name
        
        self.data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📦 聊天记录备份插件已加载，数据目录: {self.data_dir}")
    
    def _get_file_path(self, chat_id: str, is_group: bool) -> Path:
        """获取备份文件路径"""
        msg_type = "group" if is_group else "private"
        filename = f"{chat_id}_{msg_type}.json"
        return self.data_dir / filename
    
    def _should_rotate_file(self, file_path: Path) -> bool:
        """检查是否需要轮转文件（超过最大大小）"""
        if not file_path.exists():
            return False
        
        max_size = self.config.get("max_file_size_mb", 50) * 1024 * 1024
        return file_path.stat().st_size > max_size
    
    def _rotate_file(self, file_path: Path):
        """轮转文件（重命名为带时间戳的文件）"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_name = file_path.stem + f"_{timestamp}" + file_path.suffix
        new_path = file_path.parent / new_name
        file_path.rename(new_path)
        logger.info(f"📁 备份文件已轮转: {new_name}")
    
    def _save_message(
        self,
        chat_id: str,
        is_group: bool,
        role: str,
        content: str,
        sender_id: Optional[str] = None,
        sender_name: Optional[str] = None
    ):
        """保存单条消息到文件"""
        file_path = self._get_file_path(chat_id, is_group)
        
        # 检查是否需要轮转
        if self._should_rotate_file(file_path):
            self._rotate_file(file_path)
        
        # 构建消息记录
        message = {
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content
        }
        
        # 添加系统信息（如果启用）
        if self.config.get("save_system_info", True):
            if sender_id:
                message["sender_id"] = sender_id
            if sender_name:
                message["sender_name"] = sender_name
        
        # 读取或创建文件
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {
                    "messages": [],
                    "metadata": {
                        "created_at": datetime.now().isoformat(),
                        "type": "group" if is_group else "private",
                        "id": chat_id
                    }
                }
            
            # 追加消息
            data["messages"].append(message)
            data["metadata"]["updated_at"] = datetime.now().isoformat()
            data["metadata"]["message_count"] = len(data["messages"])
            
            # 写回文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"❌ 保存消息失败: {e}")
    
    def _extract_text(self, event: AstrMessageEvent) -> str:
        """从事件中提取文本内容"""
        try:
            message = event.message_obj
            if not message:
                return ""
            
            text_parts = []
            for seg in message.message:
                if hasattr(seg, 'text') and seg.text:
                    text_parts.append(seg.text)
            
            return ' '.join(text_parts).strip()
        except Exception:
            return ""
    
    def _is_group(self, event: AstrMessageEvent) -> bool:
        """判断是否为群聊消息"""
        try:
            if hasattr(event, 'is_group_message'):
                return event.is_group_message()
            group_id = event.get_group_id()
            return group_id is not None and group_id != ""
        except Exception:
            return False
    
    def _should_backup(self, event: AstrMessageEvent, is_group: bool) -> bool:
        """检查是否应该备份该消息"""
        # 检查是否启用对应类型的备份
        if is_group and not self.config.get("enable_group", True):
            return False
        if not is_group and not self.config.get("enable_private", True):
            return False
        
        # 检查群聊白名单/黑名单
        if is_group:
            group_id = event.get_group_id()
            whitelist = self.config.get("group_whitelist", [])
            blacklist = self.config.get("group_blacklist", [])
            
            if whitelist and group_id not in whitelist:
                return False
            if group_id in blacklist:
                return False
        
        return True
    
    @filter.event_message_type(EventMessageType.ALL)
    @filter.platform_adapter_type(PlatformAdapterType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        """监听接收到的消息"""
        try:
            is_group = self._is_group(event)
            
            if not self._should_backup(event, is_group):
                return
            
            content = self._extract_text(event)
            if not content:
                return
            
            # 获取聊天 ID
            chat_id = event.get_group_id() if is_group else event.get_sender_id()
            if not chat_id:
                return
            
            sender_id = event.get_sender_id()
            sender_name = None
            if hasattr(event, 'get_sender_name'):
                sender_name = event.get_sender_name()
            
            self._save_message(
                chat_id=chat_id,
                is_group=is_group,
                role="user",
                content=content,
                sender_id=sender_id,
                sender_name=sender_name
            )
            
        except Exception as e:
            logger.error(f"❌ 处理消息失败: {e}")
    
    @filter.on_decorating_result()
    async def on_bot_response(self, event: AstrMessageEvent):
        """监听机器人的回复"""
        try:
            result = event.get_result()
            if not result or not result.chain:
                return
            
            is_group = self._is_group(event)
            
            if not self._should_backup(event, is_group):
                return
            
            # 提取回复内容
            content_parts = []
            for seg in result.chain:
                if hasattr(seg, 'text') and seg.text:
                    content_parts.append(seg.text)
            
            content = ' '.join(content_parts).strip()
            if not content:
                return
            
            # 获取聊天 ID
            chat_id = event.get_group_id() if is_group else event.get_sender_id()
            if not chat_id:
                return
            
            self._save_message(
                chat_id=chat_id,
                is_group=is_group,
                role="assistant",
                content=content
            )
            
        except Exception as e:
            logger.error(f"❌ 保存机器人回复失败: {e}")
    
    async def terminate(self):
        """插件卸载时的清理工作"""
        logger.info("📦 聊天记录备份插件已卸载")
