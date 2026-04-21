import shlex
from typing import Any

from app.llm.minimax_client import MiniMaxClient
from app.llm.prompts import SYSTEM_PROMPT_BASE, build_explain_prompt
from app.models.schemas import ExplainRequest
from app.services.history_service import append_history
from app.services.safety_service import LEVEL_ORDER, check_command_safety


def explain_command(request: ExplainRequest) -> dict[str, Any]:
    safety = check_command_safety(request.command)
    local_parts = explain_parts(request.command)
    prompt = build_explain_prompt(request.command, local_parts, safety["risk_level"])
    llm_result = MiniMaxClient().generate_json(SYSTEM_PROMPT_BASE, prompt)

    if isinstance(llm_result, dict) and llm_result.get("summary"):
        summary = str(llm_result.get("summary", "")).strip()
        parts = _normalize_parts(llm_result.get("parts")) or local_parts
        notes = _as_string_list(llm_result.get("notes", []))
        risk_level = str(llm_result.get("risk_level", safety["risk_level"])).lower()
        if risk_level not in LEVEL_ORDER:
            risk_level = safety["risk_level"]
    else:
        summary = summarize_command(request.command)
        parts = local_parts
        notes = []
        risk_level = safety["risk_level"]

    if LEVEL_ORDER[safety["risk_level"]] > LEVEL_ORDER.get(risk_level, 0):
        risk_level = safety["risk_level"]
    notes = _unique([*notes, *safety["risk_reasons"], *safety["safety_tips"]])

    append_history(
        {
            "type": "explain",
            "query": "",
            "command": request.command,
            "risk_level": risk_level,
        }
    )
    return {
        "command": request.command,
        "summary": summary,
        "parts": parts,
        "risk_level": risk_level,
        "notes": notes,
    }


def explain_parts(command: str) -> list[dict[str, str]]:
    parts: list[dict[str, str]] = []
    for segment in [item.strip() for item in command.split("|")]:
        if not segment:
            continue
        try:
            tokens = shlex.split(segment)
        except ValueError:
            tokens = segment.split()
        if not tokens:
            continue
        name = tokens[0]
        if name == "find":
            parts.extend(_explain_find(tokens))
        elif name == "grep":
            parts.extend(_explain_grep(tokens))
        elif name == "wc":
            parts.append({"token": segment, "meaning": "统计输入内容，常见 -l 表示统计行数"})
        elif name in {"sort", "uniq", "head", "tail", "awk", "sed", "cut"}:
            parts.append({"token": segment, "meaning": "对文本流进行处理、筛选或格式化"})
        elif name in {"lsof", "ss", "netstat"}:
            parts.append({"token": segment, "meaning": "查看网络连接、监听端口或占用进程"})
        elif name in {"du", "df"}:
            parts.append({"token": segment, "meaning": "查看文件、目录或文件系统空间占用"})
        elif name == "rm":
            parts.append({"token": segment, "meaning": "删除文件或目录，递归强制删除风险较高"})
        elif name == "chmod":
            parts.append({"token": segment, "meaning": "修改文件或目录权限"})
        elif name == "chown":
            parts.append({"token": segment, "meaning": "修改文件或目录所有者"})
        else:
            parts.append({"token": segment, "meaning": f"执行 {name} 命令"})
    return parts


def summarize_command(command: str) -> str:
    text = command.lower()
    if "find" in text and "wc -l" in text:
        return "统计 find 匹配结果的数量。"
    if text.startswith("find "):
        return "在指定目录下按条件查找文件或目录。"
    if text.startswith("grep ") or "| grep" in text:
        return "在文本或命令输出中查找匹配关键词的行。"
    if text.startswith("lsof ") or text.startswith("ss "):
        return "查看端口或网络连接相关信息。"
    if text.startswith("rm "):
        return "删除指定文件或目录。"
    return "执行一条 Shell 命令，并按管道顺序处理输入输出。"


def _explain_find(tokens: list[str]) -> list[dict[str, str]]:
    parts = []
    if len(tokens) > 1 and not tokens[1].startswith("-"):
        parts.append({"token": f"find {tokens[1]}", "meaning": f"从 {tokens[1]} 开始递归查找"})
    else:
        parts.append({"token": "find", "meaning": "递归查找文件或目录"})
    i = 2
    while i < len(tokens):
        token = tokens[i]
        value = tokens[i + 1] if i + 1 < len(tokens) else ""
        if token == "-type" and value:
            meaning = "只匹配普通文件" if value == "f" else f"匹配类型 {value}"
            parts.append({"token": f"-type {value}", "meaning": meaning})
            i += 2
        elif token == "-name" and value:
            parts.append({"token": f"-name {value}", "meaning": f"文件名匹配 {value}"})
            i += 2
        elif token == "-mtime" and value:
            parts.append({"token": f"-mtime {value}", "meaning": "按文件修改时间过滤"})
            i += 2
        elif token == "-delete":
            parts.append({"token": "-delete", "meaning": "删除匹配到的文件或目录"})
            i += 1
        else:
            parts.append({"token": token, "meaning": "find 的过滤条件或动作"})
            i += 1
    return parts


def _explain_grep(tokens: list[str]) -> list[dict[str, str]]:
    parts = [{"token": "grep", "meaning": "按模式匹配文本行"}]
    for token in tokens[1:]:
        if token in {"-R", "-r"}:
            parts.append({"token": token, "meaning": "递归搜索目录"})
        elif token == "-i":
            parts.append({"token": token, "meaning": "忽略大小写"})
        elif token == "-c":
            parts.append({"token": token, "meaning": "输出匹配行数量"})
        elif token.startswith("-"):
            parts.append({"token": token, "meaning": "grep 选项"})
        else:
            parts.append({"token": token, "meaning": "匹配模式或搜索路径"})
    return parts


def _normalize_parts(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    parts = []
    for item in value:
        if not isinstance(item, dict):
            continue
        token = str(item.get("token", "")).strip()
        meaning = str(item.get("meaning", "")).strip()
        if token and meaning:
            parts.append({"token": token, "meaning": meaning})
    return parts


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _unique(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result

