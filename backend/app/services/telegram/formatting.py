"""TG 消息 HTML 格式化辅助。

统一使用 HTML parse_mode：只需转义动态插值部分，模板中的标签正常生效，
解决旧版 MarkdownV2 全量转义把消息自带格式一并转义、加粗/代码全部失效的问题。
"""
import html
from typing import Any


def esc(value: Any) -> str:
    """转义动态内容（容器名、错误信息等）中的 HTML 特殊字符。"""
    return html.escape(str(value), quote=False)


def b(value: Any) -> str:
    return f"<b>{esc(value)}</b>"


def code(value: Any) -> str:
    return f"<code>{esc(value)}</code>"
