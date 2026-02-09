# 🦊 AstrBot 聊天记录备份插件

实时备份聊天记录，防止对话历史丢失。

## ✨ 功能特点

- 📝 **实时备份**：每条消息即时保存，不会丢失
- 💬 **完整记录**：同时保存用户消息和机器人回复
- 📁 **分类存储**：按 QQ 号/群号分别保存
- ⚡ **轻量高效**：追加写入，对性能几乎无影响
- 🔧 **灵活配置**：支持白名单、黑名单等设置

## 📦 安装

在 AstrBot 中使用以下命令安装：

```
plugin i https://github.com/OmniTopia/astrbot_plugin_history
```

或者在 WebUI 的插件市场中搜索「聊天记录备份」。

## ⚙️ 配置项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `enable_private` | bool | true | 是否备份私聊消息 |
| `enable_group` | bool | true | 是否备份群聊消息 |
| `group_whitelist` | list | [] | 群聊白名单（为空则全部备份） |
| `group_blacklist` | list | [] | 群聊黑名单 |
| `save_system_info` | bool | true | 是否保存时间戳、昵称等信息 |
| `max_file_size_mb` | int | 50 | 单文件最大大小（MB） |

## 📁 数据存储

备份文件保存在 AstrBot 数据目录下：

```
{astrbot_data}/plugin_data/astrbot_plugin_history/
├── 123456789_private.json    # 私聊记录
├── 987654321_group.json      # 群聊记录
└── ...
```

### 文件格式

```json
{
  "metadata": {
    "created_at": "2026-02-09T00:00:00",
    "updated_at": "2026-02-09T12:00:00",
    "type": "private",
    "id": "123456789",
    "message_count": 100
  },
  "messages": [
    {
      "timestamp": "2026-02-09T10:30:00",
      "role": "user",
      "content": "你好！",
      "sender_id": "123456789",
      "sender_name": "用户A"
    },
    {
      "timestamp": "2026-02-09T10:30:05",
      "role": "assistant",
      "content": "你好呀～有什么可以帮你的吗？"
    }
  ]
}
```

## 🔄 文件轮转

当单个备份文件超过 `max_file_size_mb` 设置的大小时，会自动创建新文件：

```
123456789_private.json           # 当前文件
123456789_private_20260209_120000.json  # 历史文件
```

## ❓ 常见问题

### Q: 会影响机器人性能吗？
A: 几乎不会。插件使用追加写入模式，每条消息只需几毫秒即可保存。

### Q: 一天大概占用多少空间？
A: 取决于消息量。一般来说，每天 100 条私聊 + 500 条群聊约占用 1-3 MB。

### Q: 数据在哪里可以查看？
A: 在 AstrBot 的数据目录下找到 `plugin_data/astrbot_plugin_history/` 文件夹。

### Q: 可以导出用于 AI 微调吗？
A: 可以！备份格式与标准对话格式兼容，可以方便地转换为微调数据集。

## 🦊 关于

由 [OmniTopia](https://github.com/OmniTopia) 开发 - 全一的乌托邦

让每一段对话都不会丢失 💕
