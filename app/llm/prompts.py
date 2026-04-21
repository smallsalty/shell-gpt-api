import json


SYSTEM_PROMPT_BASE = """你是一个谨慎、简洁的 shell 命令助手。
优先输出安全、标准、常见、可解释的 Bash / Unix / Linux 命令。
如果需求有风险，必须在 risk_level、risk_reasons、safety_tips 中说明。
输出必须是单个 JSON 对象，不要输出 Markdown 代码块，不要输出多余说明。
如果请求本身危险，可以解释风险，但不要鼓励用户直接执行危险命令。
候选命令最多 3 条，主命令只给 1 条。"""


def build_generate_prompt(
    query: str,
    shell_type: str,
    os_name: str,
    context: str,
    skills_prompt: str,
) -> str:
    payload = {
        "task": "natural_language_to_shell_command",
        "query": query,
        "shell_type": shell_type,
        "os": os_name,
        "context": context,
        "matched_skills": skills_prompt,
        "risk_constraints": [
            "避免生成 rm -rf /、mkfs、dd 写磁盘、curl|sh 等高风险命令。",
            "删除、覆盖、修改权限、安装软件等操作需要给出风险提示。",
            "优先给出可预览、范围明确、可解释的命令。",
        ],
        "output_schema": {
            "command": "string",
            "alternatives": ["string, max 3"],
            "explanation": "string",
            "risk_level": "low|medium|high",
            "risk_reasons": ["string"],
            "safety_tips": ["string"],
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_explain_prompt(command: str, local_parts: list[dict], risk_level: str) -> str:
    payload = {
        "task": "explain_shell_command",
        "command": command,
        "local_parts": local_parts,
        "local_risk_level": risk_level,
        "requirements": [
            "解释命令作用、关键参数含义、预期结果和适用场景。",
            "保持简洁，不要扩展无关内容。",
            "风险判断要尊重 local_risk_level。",
        ],
        "output_schema": {
            "summary": "string",
            "parts": [{"token": "string", "meaning": "string"}],
            "risk_level": "low|medium|high",
            "notes": ["string"],
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)

