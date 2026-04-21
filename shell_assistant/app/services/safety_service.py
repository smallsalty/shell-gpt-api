import re
import shlex


LEVEL_ORDER = {"low": 0, "medium": 1, "high": 2}


def check_command_safety(command: str) -> dict:
    text = command.strip()
    lower = re.sub(r"\s+", " ", text.lower())
    reasons: list[str] = []
    tips: list[str] = []
    level = "low"

    def add(new_level: str, reason: str, *new_tips: str) -> None:
        nonlocal level
        if LEVEL_ORDER[new_level] > LEVEL_ORDER[level]:
            level = new_level
        if reason not in reasons:
            reasons.append(reason)
        for tip in new_tips:
            if tip and tip not in tips:
                tips.append(tip)

    for target in _rm_rf_targets(text):
        clean = target.strip("'\"")
        if clean in {"/", "/*"} or clean.startswith(("/etc", "/usr", "/bin", "/sbin", "/lib", "/boot")):
            add(
                "high",
                "检测到递归强制删除系统或根目录相关路径",
                "避免对根目录或系统目录执行删除",
                "建议先用 ls 或 find 确认目标文件",
            )
        else:
            add(
                "medium",
                "检测到 rm -rf 递归强制删除命令",
                "建议先去掉 -f 或改用 echo/find -print 预览",
                "确认路径范围后再执行删除",
            )

    if re.search(r"\bmkfs(?:\.\w+)?\b", lower):
        add("high", "检测到格式化文件系统命令 mkfs", "格式化会清空目标设备数据")
    if re.search(r"\bdd\b.*\bof=/dev/", lower):
        add("high", "检测到 dd 写入块设备", "确认 if/of 参数，避免覆盖磁盘或分区")
    if ":(){:|:&};:" in re.sub(r"\s+", "", lower):
        add("high", "检测到 fork bomb 模式", "不要执行会耗尽系统进程资源的命令")
    if re.search(r"\b(shutdown|reboot|poweroff)\b", lower) or re.search(r"\binit\s+0\b", lower):
        add("high", "检测到关机或重启命令", "确认不会影响正在运行的服务和用户")
    if re.search(r"\bchmod\b.*(?:-r|--recursive).*777\s+/", lower):
        add("high", "检测到对根路径递归设置 777 权限", "不要给系统路径开放全局写权限")
    if re.search(r"\bchown\b.*(?:-r|--recursive)\b", lower):
        add("high", "检测到递归修改所有者", "递归 chown 可能破坏系统权限")
    if re.search(r"(?:^|[^2])>{1,2}\s*/etc/", lower):
        add("high", "检测到重定向写入 /etc 系统配置路径", "修改系统配置前先备份并确认内容")
    if re.search(r"\b(curl|wget)\b.+\|\s*(?:sudo\s+)?(?:sh|bash)\b", lower):
        add("high", "检测到下载脚本后直接交给 shell 执行", "先保存并审查脚本内容，确认来源可信")

    if re.search(r"\bkill\s+-9\b", lower):
        add("medium", "检测到 kill -9 强制终止进程", "优先尝试普通 kill，确认 PID 后再执行")
    if re.search(r"\biptables\b", lower):
        add("medium", "检测到防火墙规则修改命令", "错误规则可能中断网络连接")
    if re.search(r"\buserdel\b", lower):
        add("medium", "检测到删除用户命令", "删除用户前确认数据和服务归属")
    if re.search(r"\b(?:mv|cp)\b.+\s/(?:etc|usr|bin|sbin|lib|boot)(?:/|\s|$)", lower):
        add("medium", "检测到对敏感系统路径执行复制或移动", "写入系统路径前先备份并确认权限")
    if re.search(r"\bsed\b.*\s-i\b|\bsed\b.*\s-i['\"]?", lower):
        if re.search(r"/(?:etc|boot|usr|bin|sbin|lib)/", lower):
            add("medium", "检测到原地修改关键配置路径", "建议先备份文件或去掉 -i 预览")
        else:
            add("medium", "检测到 sed -i 原地替换", "建议先备份文件或去掉 -i 预览")
    if re.search(r"\btruncate\b.+/(?:etc|boot|usr|bin|sbin|lib)/", lower):
        add("medium", "检测到清空或截断关键路径文件", "确认目标文件并先备份")
    if re.search(r"\bfind\b.+\s-delete\b", lower):
        add("medium", "检测到 find -delete 批量删除", "建议先把 -delete 改成 -print 预览")
    if re.search(r"\bxargs\s+rm\b", lower):
        add("medium", "检测到通过 xargs 批量删除", "建议先输出待删除列表确认范围")

    if level != "low" and not tips:
        tips.append("执行前请确认目标路径、权限和影响范围")

    return {"risk_level": level, "risk_reasons": reasons, "safety_tips": tips}


def _rm_rf_targets(command: str) -> list[str]:
    targets: list[str] = []
    for segment in re.split(r"[;&|]+", command):
        segment = segment.strip()
        if not segment.lower().startswith("rm "):
            continue
        try:
            parts = shlex.split(segment)
        except ValueError:
            parts = segment.split()
        opts = [part for part in parts[1:] if part.startswith("-")]
        has_recursive = any("r" in opt.lower() or opt.lower() == "--recursive" for opt in opts)
        has_force = any("f" in opt.lower() or opt.lower() == "--force" for opt in opts)
        if not (has_recursive and has_force):
            continue
        for part in parts[1:]:
            if not part.startswith("-"):
                targets.append(part)
    return targets or []

