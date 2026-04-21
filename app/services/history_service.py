import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import get_settings


def append_history(record: dict[str, Any]) -> None:
    settings = get_settings()
    path = settings.history_path
    records = read_history()
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **record,
    }
    records.append(record)
    records = records[-settings.history_limit :]
    _write_json(path, records)


def record_command(command: str, query: str = "", risk_level: str = "low") -> None:
    append_history({"query": query, "command": command, "risk_level": risk_level})


def read_history() -> list[dict[str, Any]]:
    path = get_settings().history_path
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def recent_commands(limit: int = 10) -> list[dict[str, Any]]:
    commands = []
    seen = set()
    for item in reversed(read_history()):
        command = str(item.get("command", "")).strip()
        if not command or command in seen:
            continue
        commands.append(
            {
                "timestamp": item.get("timestamp", ""),
                "query": item.get("query", ""),
                "command": command,
                "risk_level": item.get("risk_level", "low"),
            }
        )
        seen.add(command)
        if len(commands) >= limit:
            break
    return commands


def build_highlights() -> dict[str, Any]:
    records = read_history()
    categories = Counter(_categorize(item) for item in records)
    patterns = Counter()
    high_risk_count = 0

    for item in records:
        if item.get("risk_level") == "high":
            high_risk_count += 1
        for pattern in _command_patterns(item.get("command", "")):
            patterns[pattern] += 1

    top_categories = [
        {"name": name, "count": count} for name, count in categories.most_common(5)
    ]
    frequent_patterns = [name for name, _ in patterns.most_common(8)]
    summary = _summary(top_categories, high_risk_count)
    return {
        "total_records": len(records),
        "top_categories": top_categories,
        "high_risk_count": high_risk_count,
        "frequent_patterns": frequent_patterns,
        "summary": summary,
    }


def _write_json(path: Path, data: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _categorize(record: dict[str, Any]) -> str:
    text = f"{record.get('query', '')} {record.get('command', '')}".lower()
    rules = [
        ("文件查找", ["find", "locate", "查找", "找文件", "pdf", "文件"]),
        ("文本处理", ["grep", "awk", "sed", "sort", "uniq", "cut", "wc", "日志", "error"]),
        ("进程管理", ["ps", "kill", "pgrep", "pkill", "lsof", "进程"]),
        ("网络排查", ["ping", "curl", "wget", "ss", "netstat", "nslookup", "dig", "端口"]),
        ("权限与用户", ["chmod", "chown", "sudo", "whoami", "userdel", "权限", "用户"]),
        ("压缩归档", ["tar", "zip", "unzip", "gzip", "压缩", "解压"]),
        ("包管理", ["apt", "yum", "dnf", "pip", "npm", "安装"]),
        ("系统资源", ["df", "du", "free", "uname", "磁盘", "内存"]),
    ]
    for name, keys in rules:
        if any(key in text for key in keys):
            return name
    return "其他"


def _command_patterns(command: str) -> list[str]:
    return re.findall(r"(?:^|[|;&]\s*)([a-zA-Z][\w.-]*)", command)


def _summary(top_categories: list[dict[str, Any]], high_risk_count: int) -> str:
    if not top_categories:
        return "暂无历史记录。"
    names = "、".join(item["name"] for item in top_categories[:3])
    risk_text = (
        f"出现过 {high_risk_count} 次高风险命令。"
        if high_risk_count
        else "暂未出现高风险命令。"
    )
    return f"最近操作以{names}为主，{risk_text}"
