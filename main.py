import json
import os
import sqlite3
from typing import Any

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register


@register(
    "astrbot_plugin_reset_all_contexts",
    "批量重置上下文",
    "管理员命令，一次清空所有群聊和私聊的 AstrBot 短期上下文",
    "1.0.1",
)
class ResetAllContextsPlugin(Star):
    PREVIEW_COMMAND = "reset_all_preview"
    CONFIRM_COMMAND = "reset_all_confirm"

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

    def _db_path(self) -> str:
        return str(self.config.get("db_path", "/AstrBot/data/data_v4.db") or "").strip()

    def _confirm_word(self) -> str:
        return str(self.config.get("confirm_word", "确认重置全部") or "").strip()

    def _connect(self) -> sqlite3.Connection:
        db_path = self._db_path()
        if not db_path:
            raise RuntimeError("未配置数据库路径")
        if not os.path.exists(db_path):
            raise RuntimeError(f"数据库不存在: {db_path}")
        conn = sqlite3.connect(db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _message_count(content: Any) -> int:
        if content is None:
            return 0
        if isinstance(content, str):
            text = content.strip()
            if not text:
                return 0
            try:
                data = json.loads(text)
            except Exception:
                return 1
        else:
            data = content
        if isinstance(data, list):
            return len(data)
        return 1

    def _load_rows(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT rowid AS __rowid__, * FROM conversations ORDER BY rowid"
            )
            return [dict(row) for row in cursor.fetchall()]

    def _analyze(self) -> tuple[int, int, int]:
        rows = self._load_rows()
        nonempty_rows = 0
        total_messages = 0
        for row in rows:
            count = self._message_count(row.get("content"))
            if count > 0:
                nonempty_rows += 1
                total_messages += count
        return len(rows), nonempty_rows, total_messages

    def _reset_all(self) -> tuple[int, int, int]:
        rows = self._load_rows()
        rows_to_clear = [
            row for row in rows if self._message_count(row.get("content")) > 0
        ]

        if not rows_to_clear:
            return len(rows), 0, 0

        rowids = [int(row["__rowid__"]) for row in rows_to_clear]
        placeholders = ",".join("?" for _ in rowids)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE conversations SET content = '[]' WHERE rowid IN ({placeholders})",
                rowids,
            )
            conn.commit()

        total_messages = sum(
            self._message_count(row.get("content")) for row in rows_to_clear
        )
        return len(rows), len(rows_to_clear), total_messages

    @staticmethod
    def _first_token(message: str) -> str:
        return (message or "").strip().split(maxsplit=1)[0] if (message or "").strip() else ""

    def _invoked_command_text(self, event: AstrMessageEvent, command_name: str) -> str:
        token = self._first_token(str(getattr(event, "message_str", "") or ""))
        if token.endswith(command_name):
            return token
        return command_name

    def _suggest_command(self, event: AstrMessageEvent, command_name: str) -> str:
        preview_token = self._invoked_command_text(event, self.PREVIEW_COMMAND)
        if preview_token.endswith(self.PREVIEW_COMMAND):
            prefix = preview_token[: -len(self.PREVIEW_COMMAND)]
            return f"{prefix}{command_name}"
        return command_name

    def _extract_arg_text(
        self,
        event: AstrMessageEvent,
        command_name: str,
        args: tuple[Any, ...],
    ) -> str:
        if args:
            text = " ".join(str(arg) for arg in args if arg is not None).strip()
            if text:
                return text

        message = str(getattr(event, "message_str", "") or "").strip()
        if not message:
            return ""
        parts = message.split(maxsplit=1)
        if len(parts) == 1:
            return ""

        command_token, rest = parts
        if command_token.endswith(command_name):
            return rest.strip()
        return rest.strip()

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command(PREVIEW_COMMAND)
    async def reset_all_preview(self, event: AstrMessageEvent):
        try:
            total_rows, nonempty_rows, total_messages = self._analyze()
            confirm_command = self._suggest_command(event, self.CONFIRM_COMMAND)
            yield event.plain_result(
                "批量重置预览：\n"
                f"- 会话总数：{total_rows}\n"
                f"- 有短期上下文的会话：{nonempty_rows}\n"
                f"- 预计清空消息条数：{total_messages}\n"
                f"\n确认执行请发送：{confirm_command} {self._confirm_word()}"
            )
        except Exception as e:
            logger.error(f"[ResetAllContexts] 预览失败: {e}", exc_info=True)
            yield event.plain_result(f"预览失败：{e}")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command(CONFIRM_COMMAND)
    async def reset_all_confirm(self, event: AstrMessageEvent, *args):
        confirm_word = self._confirm_word()
        given = self._extract_arg_text(event, self.CONFIRM_COMMAND, args)
        invoked_command = self._invoked_command_text(event, self.CONFIRM_COMMAND)

        if given != confirm_word:
            yield event.plain_result(
                "确认词不匹配，未执行。\n"
                f"如需执行，请发送：{invoked_command} {confirm_word}"
            )
            return

        try:
            total_rows, cleared_rows, total_messages = self._reset_all()
            yield event.plain_result(
                "批量重置完成。\n"
                f"- 会话总数：{total_rows}\n"
                f"- 已清空会话：{cleared_rows}\n"
                f"- 已清空消息条数：{total_messages}"
            )
        except Exception as e:
            logger.error(f"[ResetAllContexts] 批量重置失败: {e}", exc_info=True)
            yield event.plain_result(f"批量重置失败：{e}")

    async def terminate(self):
        logger.info("[ResetAllContexts] 插件已卸载")
