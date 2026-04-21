import subprocess
from typing import Any

from app.models.schemas import GenerateRequest
from app.services.command_service import generate_command
from app.services.history_service import recent_commands, record_command
from app.services.safety_service import check_command_safety


def interactive_main() -> None:
    print("Shell-GPT Linux 终端助手")
    print("输入中文需求生成 Shell 命令；输入 :help 查看帮助，输入 :q 退出。")

    while True:
        try:
            query = input("\n请输入需求: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已退出。")
            return

        if not query:
            continue
        if query in {":q", ":quit"}:
            print("已退出。")
            return
        if query == ":help":
            _print_help()
            continue
        if query == ":history":
            _print_history()
            continue

        try:
            result = generate_command(GenerateRequest(query=query))
        except Exception as exc:
            print(f"生成命令失败: {exc}")
            continue

        commands = _candidate_commands(result)
        if not commands:
            print("没有生成可执行命令。")
            continue

        _print_recommendation(result, commands)
        choice = input("输入编号准备执行，输入 n 跳过，输入 q 退出: ").strip().lower()
        if choice in {"q", ":q", ":quit"}:
            print("已退出。")
            return
        if choice in {"", "n", "no"}:
            print("已跳过。")
            continue
        if not choice.isdigit() or not (1 <= int(choice) <= len(commands)):
            print("选择无效，已跳过。")
            continue

        command = commands[int(choice) - 1]
        _confirm_and_run(command)


def main() -> None:
    interactive_main()


def _candidate_commands(result: dict[str, Any]) -> list[str]:
    commands = []
    primary = str(result.get("command", "")).strip()
    if primary:
        commands.append(primary)
    for item in result.get("alternatives", []) or []:
        command = str(item).strip()
        if command and command not in commands:
            commands.append(command)
    return commands[:4]


def _print_recommendation(result: dict[str, Any], commands: list[str]) -> None:
    print("\n推荐命令:")
    for index, command in enumerate(commands, start=1):
        safety = check_command_safety(command)
        print(f"[{index}] {command}")
        print(f"    风险等级: {safety['risk_level']}")

    explanation = str(result.get("explanation", "")).strip()
    if explanation:
        print("\n解释:")
        print(explanation)

    primary_safety = check_command_safety(commands[0])
    _print_safety(primary_safety)


def _confirm_and_run(command: str) -> bool:
    print("\n准备执行:")
    print(command)
    edited = input("直接回车执行；输入新命令可修改；输入 n 取消: ").strip()
    if edited in {"q", ":q", ":quit"}:
        print("已退出。")
        raise SystemExit
    if edited.lower() in {"n", "no"}:
        print("已取消执行。")
        return False
    if edited:
        command = edited

    safety = check_command_safety(command)
    print(f"\n最终命令: {command}")
    _print_safety(safety)

    if safety["risk_level"] == "high":
        print("高风险命令已被拒绝执行。")
        return False

    if safety["risk_level"] == "medium":
        confirm = input("该命令存在中等风险，输入 yes 确认执行: ").strip()
        if confirm != "yes":
            print("已取消执行。")
            return False

    print("\n开始执行:\n")
    completed = subprocess.run(command, shell=True)
    if completed.returncode != 0:
        print(f"\n命令失败，退出码: {completed.returncode}")
    record_command(command, risk_level=safety["risk_level"])
    return True


def _print_safety(safety: dict[str, Any]) -> None:
    print(f"\n风险等级: {safety['risk_level']}")
    if safety.get("risk_reasons"):
        print("风险原因:")
        for item in safety["risk_reasons"]:
            print(f"- {item}")
    if safety.get("safety_tips"):
        print("安全提示:")
        for item in safety["safety_tips"]:
            print(f"- {item}")


def _print_history() -> None:
    items = recent_commands(10)
    if not items:
        print("\n暂无历史命令。")
        return

    print("\n最近命令:")
    for index, item in enumerate(items, start=1):
        print(f"[{index}] {item['command']}")

    choice = input("输入编号复刻执行，输入 n 返回: ").strip().lower()
    if choice in {"", "n", "no"}:
        return
    if not choice.isdigit() or not (1 <= int(choice) <= len(items)):
        print("选择无效。")
        return
    _confirm_and_run(items[int(choice) - 1]["command"])


def _print_help() -> None:
    print(
        """
可输入中文需求，例如：
  查找当前目录下所有 pdf 文件
  查看 8080 端口被谁占用
  统计 logs 目录下包含 error 的行数

特殊指令：
  :help     查看帮助
  :history  查看历史亮点
  :q        退出
  :quit     退出
""".strip()
    )


if __name__ == "__main__":
    main()
