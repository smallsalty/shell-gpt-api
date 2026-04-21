import re
from typing import Any

from app.llm.minimax_client import MiniMaxClient
from app.llm.prompts import SYSTEM_PROMPT_BASE, build_generate_prompt
from app.models.schemas import GenerateRequest
from app.services.history_service import append_history
from app.services.safety_service import LEVEL_ORDER, check_command_safety
from app.skills.skill_loader import build_skills_prompt, select_relevant_skills


def generate_command(request: GenerateRequest) -> dict[str, Any]:
    skills = select_relevant_skills(request.query)
    skills_prompt = build_skills_prompt(skills)
    prompt = build_generate_prompt(
        query=request.query,
        shell_type=request.shell_type,
        os_name=request.os,
        context=request.context,
        skills_prompt=skills_prompt,
    )
    llm_result = MiniMaxClient().generate_json(SYSTEM_PROMPT_BASE, prompt)

    if isinstance(llm_result, dict) and llm_result.get("command"):
        result = _normalize_llm_result(request.query, llm_result)
        source = "llm+skills"
    else:
        result = _fallback_generate(request.query, skills)
        source = "skills-fallback"

    intent_safety = _check_query_intent_risk(request.query)
    if _is_disk_destructive_intent(request.query):
        result["command"] = "lsblk -f"
        result["alternatives"] = _unique(["lsblk", "df -h", *result.get("alternatives", [])])[:3]
        result["explanation"] = (
            "格式化磁盘是高危操作，会永久删除目标设备数据。当前仅提供只读查看命令，"
            "用于确认磁盘和分区信息，不直接执行格式化。"
        )

    safety = check_command_safety(result["command"])
    result["risk_level"] = _max_level(
        _max_level(safety["risk_level"], str(result.get("risk_level", "low"))),
        intent_safety["risk_level"],
    )
    result["risk_reasons"] = _merge_list(
        intent_safety["risk_reasons"],
        _merge_list(safety["risk_reasons"], result.get("risk_reasons", [])),
    )
    result["safety_tips"] = _merge_list(
        intent_safety["safety_tips"],
        _merge_list(safety["safety_tips"], result.get("safety_tips", [])),
    )
    result["source"] = source

    append_history(
        {
            "type": "generate",
            "query": request.query,
            "command": result["command"],
            "risk_level": result["risk_level"],
        }
    )
    return result


def _normalize_llm_result(query: str, data: dict[str, Any]) -> dict[str, Any]:
    command = str(data.get("command", "")).strip()
    alternatives = data.get("alternatives", [])
    if not isinstance(alternatives, list):
        alternatives = []
    alternatives = [str(item).strip() for item in alternatives if str(item).strip()]
    alternatives = _unique([item for item in alternatives if item != command])[:3]
    risk_level = str(data.get("risk_level", "low")).lower()
    if risk_level not in LEVEL_ORDER:
        risk_level = "low"
    return {
        "query": query,
        "command": command,
        "alternatives": alternatives,
        "explanation": str(data.get("explanation", "")).strip() or "生成的 Shell 命令。",
        "risk_level": risk_level,
        "risk_reasons": _as_string_list(data.get("risk_reasons", [])),
        "safety_tips": _as_string_list(data.get("safety_tips", [])),
    }


def _fallback_generate(query: str, skills: list[dict]) -> dict[str, Any]:
    q = query.lower()
    command = ""
    explanation = "根据内置 NL2Bash 技能模板生成的命令。"
    alternatives: list[str] = []

    if _is_disk_destructive_intent(query):
        command = "lsblk -f"
        alternatives = ["lsblk", "df -h"]
        explanation = "格式化磁盘是高危操作；当前仅提供只读查看命令，用于确认磁盘和分区信息。"
    elif any(key in q for key in ["pdf", "所有 pdf", "pdf 文件"]):
        command = "find . -type f -name '*.pdf'"
        explanation = "在当前目录及子目录中查找所有 PDF 文件。"
    elif "8080" in q and any(key in q for key in ["端口", "占用", "port"]):
        command = "lsof -i :8080"
        alternatives = ["ss -ltnp 'sport = :8080'"]
        explanation = "查看 8080 端口被哪个进程占用。"
    elif "端口" in q or "port" in q:
        port = _extract_number(q) or "<port>"
        command = f"lsof -i :{port}"
        alternatives = [f"ss -ltnp 'sport = :{port}'"]
        explanation = f"查看 {port} 端口的占用进程。"
    elif "logs" in q and "error" in q and any(key in q for key in ["统计", "行数", "count"]):
        command = 'grep -R "error" logs | wc -l'
        explanation = "统计 logs 目录下包含 error 的匹配行数。"
    elif any(key in q for key in ["临时文件", "temporary", "tmp"]) and any(
        key in q for key in ["删除", "clean", "remove"]
    ):
        command = "find . -type f \\( -name '*.tmp' -o -name '*~' \\) -print"
        alternatives = ["find . -type f \\( -name '*.tmp' -o -name '*~' \\) -delete"]
        explanation = "先列出当前目录下常见临时文件；确认后可使用替代命令删除。"
    elif any(key in q for key in ["最大", "大文件", "largest"]):
        command = "du -ah . | sort -hr | head -n 10"
        explanation = "列出当前目录下占用空间最大的 10 个条目。"
    elif any(key in q for key in ["error", "包含", "关键词", "grep"]):
        command = 'grep -R "<keyword>" .'
        explanation = "递归查找包含指定关键词的文本行。"
    elif any(key in q for key in ["数量", "统计", "count"]):
        command = "find . -type f | wc -l"
        explanation = "统计当前目录及子目录中的文件数量。"
    elif skills:
        command = skills[0].get("command_templates", [""])[0]
        explanation = f"使用技能模板：{skills[0].get('intent', '常见 Shell 任务')}。"

    if not command:
        command = "printf '%s\\n' '无法仅凭本地规则生成可靠命令，请配置 LLM_API_KEY 后重试。'"
        explanation = "未配置 LLM 或本地模板未匹配到可靠命令。"

    return {
        "query": query,
        "command": command,
        "alternatives": alternatives[:3],
        "explanation": explanation,
        "risk_level": "low",
        "risk_reasons": [],
        "safety_tips": [],
    }


def _extract_number(text: str) -> str | None:
    match = re.search(r"\b(\d{2,5})\b", text)
    return match.group(1) if match else None


def _check_query_intent_risk(query: str) -> dict[str, Any]:
    command_safety = check_command_safety(query)
    level = command_safety["risk_level"]
    reasons = list(command_safety["risk_reasons"])
    tips = list(command_safety["safety_tips"])
    q = query.lower()

    def add(new_level: str, reason: str, *new_tips: str) -> None:
        nonlocal level
        level = _max_level(level, new_level)
        if reason not in reasons:
            reasons.append(reason)
        for tip in new_tips:
            if tip and tip not in tips:
                tips.append(tip)

    if _is_disk_destructive_intent(query):
        add(
            "high",
            "用户需求涉及格式化、清空或覆盖磁盘，真实执行会永久删除目标设备数据",
            "当前推荐命令仅用于查看磁盘信息，不执行格式化",
            "先确认设备名，例如 /dev/sdb，而不是系统盘",
            "确保重要数据已备份",
            "不要在未确认目标设备前执行 mkfs、dd 等写盘命令",
        )

    if any(key in q for key in ["删除根目录", "清空根目录", "删除系统目录"]):
        add(
            "high",
            "用户需求涉及删除根目录或系统目录",
            "不要对 /、/etc、/usr、/boot 等系统路径执行递归删除",
            "先用 ls 或 find -print 确认目标范围",
        )

    restart_intent = "重启" in q and not any(key in q for key in ["记录", "日志", "时间", "历史", "查看"])
    if restart_intent or any(key in q for key in ["关机", "shutdown", "reboot", "poweroff", "init 0"]):
        add(
            "high",
            "用户需求涉及关机或重启，会中断当前机器上的服务和会话",
            "确认没有正在运行的关键任务或远程用户后再操作",
        )

    return {"risk_level": level, "risk_reasons": reasons, "safety_tips": tips}


def _is_disk_destructive_intent(query: str) -> bool:
    q = query.lower()
    disk_terms = ["磁盘", "硬盘", "分区", "/dev/", "disk", "drive", "partition"]
    has_disk = any(term in q for term in disk_terms)
    if "mkfs" in q:
        return True
    if any(term in q for term in ["格式化", "format"]) and has_disk:
        return True
    if any(term in q for term in ["清空", "擦除", "抹掉", "wipe"]) and has_disk:
        return True
    if "dd" in q and any(term in q for term in ["of=/dev", "写入磁盘", "写入硬盘", "写盘", "覆盖磁盘"]):
        return True
    return False


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _merge_list(first: list[str], second: list[str]) -> list[str]:
    return _unique([*first, *_as_string_list(second)])


def _unique(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result


def _max_level(first: str, second: str) -> str:
    first = first if first in LEVEL_ORDER else "low"
    second = second if second in LEVEL_ORDER else "low"
    return first if LEVEL_ORDER[first] >= LEVEL_ORDER[second] else second
