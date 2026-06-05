# 批量重置上下文

这是一个 AstrBot 管理员插件，用来一次性清空当前 AstrBot 数据库里所有群聊、私聊会话的短期上下文。

它适合用在：普通 `reset` 只能重置当前会话，但你想把这个 bot 已记录的所有会话窗口都统一重置一遍。

## 它会做什么

- 扫描 AstrBot 的 `conversations` 表。
- 统计哪些会话里还有短期上下文。
- 执行确认命令后，把这些会话的 `content` 字段清空为 `[]`。
- 只在你发送命令的当前会话里返回汇总结果。

## 它不会做什么

- 不会删除 corememory 等长期记忆插件的数据。
- 不会删除人格、人设、配置、知识库。
- 不会给每个群聊或私聊都发送“清除聊天历史成功”。
- 不会备份被清空的短期上下文。
- 不会逐个模拟官方 `reset` 的完整事件流程。

## 和官方 reset 的区别

官方 `reset` 面向当前会话，会清理当前会话上下文，并可能触发 AstrBot 内部的当前会话重置流程。

本插件是批量数据库清理工具，目标是静默清空所有已知会话的短期上下文。它不会对每个会话分别发送 `reset`，所以不会刷屏。

## 安装

把整个插件目录放到 AstrBot 插件目录：

```text
/AstrBot/data/plugins/astrbot_plugin_reset_all_contexts
```

Docker 部署时，如果 `/AstrBot/data` 挂载到了宿主机，例如：

```text
/root/astrbot/data -> /AstrBot/data
```

那宿主机目录就是：

```text
/root/astrbot/data/plugins/astrbot_plugin_reset_all_contexts
```

放好后重启 AstrBot 或在 WebUI 里重载插件。

## 命令

命令前缀跟随 AstrBot 当前配置，不写死 `/`。

如果群聊唤醒词是 `+`，群聊里发送：

```text
+reset_all_preview
+reset_all_confirm 确认重置全部
```

如果私聊不需要唤醒词，私聊里发送：

```text
reset_all_preview
reset_all_confirm 确认重置全部
```

建议先预览。预览命令会返回：

- 会话总数
- 有短期上下文的会话数
- 预计清空的消息条数
- 按你当前实际命令前缀生成的确认命令

确认执行后会返回：

- 会话总数
- 已清空会话数
- 已清空消息条数

如果没有看到“批量重置完成”和统计数字，就不要当作执行成功。

## 权限

两个命令都要求 AstrBot 管理员权限。

只要发送者是 AstrBot 配置里的管理员 ID，不管是在群聊还是私聊发送命令，都可以触发全局批量重置。

## 配置

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `db_path` | `/AstrBot/data/data_v4.db` | AstrBot 数据库路径。Docker 默认通常不用改。 |
| `confirm_word` | `确认重置全部` | 执行确认词，用来防止误触。 |

## 注意

这个操作不可恢复。执行前请先用 `reset_all_preview` 看清楚会影响多少会话。

如果你想保留短期上下文，请先自行备份 `/AstrBot/data/data_v4.db`。
