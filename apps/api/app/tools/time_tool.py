"""时间工具。

返回服务端当前时间，包含机器可读和人类可读格式。
"""

from datetime import datetime


def tool_get_server_time() -> dict[str, str]:
    now = datetime.now()
    return {
        "iso": now.isoformat(timespec="seconds"),
        "human": now.strftime("%Y-%m-%d %H:%M:%S"),
    }

