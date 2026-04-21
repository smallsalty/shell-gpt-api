# Shell-GPT Linux 终端助手

这是一个面向 Linux 终端的最小可运行 Shell 命令助手。用户用中文或英文描述想做的事情，程序会生成候选 Shell 命令、解释命令含义、标注风险等级；用户选择命令后，程序会把命令预填到终端输入框中，用户可以直接编辑，按 Enter 后执行。

项目目标不是做一个网站，而是做一个能在 Linux 虚拟机终端中直接使用的智能命令行工具。FastAPI 接口仍然保留，但只是辅助能力，主入口是 `python shellgpt.py`。

## 功能效果

核心能力：

- 自然语言转 Shell 命令：例如输入“查找当前目录下所有 pdf 文件”，生成 `find . -type f -name '*.pdf'`。
- 命令解释：说明命令用途、参数含义、预期结果。
- 危险命令识别：对 `rm -rf /`、`mkfs`、`dd of=/dev/...`、`curl | sh` 等命令做高风险提示。
- 终端内执行：用户选择命令后，可以在输入框中直接编辑命令，再按 Enter 执行。
- 历史复刻：`:history` 显示最近 10 条具体命令，选择编号后可以复刻并继续编辑执行。
- 本地 fallback：MiniMax 不可用时，仍能通过内置 NL2Bash skills 生成常见命令。

## 安装

在 Linux 虚拟机中进入项目目录：

```bash
cd /path/to/shell-gpt
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

编辑 `.env`：

```env
LLM_API_KEY=your_key
LLM_BASE_URL=https://api.minimaxi.com/anthropic
LLM_MODEL=MiniMax-M2.7
LLM_TIMEOUT_SECONDS=25
LLM_MAX_TOKENS=2048
HISTORY_LIMIT=10
```

说明：

- `LLM_API_KEY` 是 MiniMax API Key。
- `LLM_BASE_URL` 使用 MiniMax Anthropic-compatible API 地址。
- 不要配置成 OpenAI 风格的 `/chat/completions` 地址。
- 如果不配置 `LLM_API_KEY`，程序仍会使用本地 skills fallback 支持部分常见命令。

## 终端交互运行

推荐入口：

```bash
python shellgpt.py
```

也可以通过 CLI 子命令启动：

```bash
python -m app.cli interactive
```

启动后输入需求：

```text
请输入需求: 查找当前目录下所有 pdf 文件
```

程序输出候选命令：

```text
推荐命令:
[1] find . -type f -name '*.pdf'
    风险等级: low

解释:
在当前目录及子目录中查找所有 PDF 文件。

风险等级: low
输入编号准备执行，输入 n 跳过，输入 q 退出: 1
```

选择编号后进入准备执行阶段：

```text
准备执行，Enter 执行，可直接编辑命令:
> find . -type f -name '*.pdf'
```

这里的命令已经在输入框中，用户可以直接按 Enter 执行，也可以用方向键、Backspace、Ctrl+A、Ctrl+E 等终端编辑方式修改命令。最终输入框里的内容会作为实际执行命令。

执行成功时，程序只显示命令自身输出，不额外打印 `退出码: 0`。执行失败时才显示：

```text
命令失败，退出码: <code>
```

## 交互指令

```text
:help     查看帮助
:history  查看最近 10 条命令并复刻
:q        退出
:quit     退出
```

历史复刻示例：

```text
请输入需求: :history

最近命令:
[1] find . -type f -name '*.pdf'
[2] lsof -i :8080

输入编号复刻执行，输入 n 返回: 1

准备执行，Enter 执行，可直接编辑命令:
> find . -type f -name '*.pdf'
```

历史命令复刻不会绕过安全检查。选择历史命令后仍然进入准备执行阶段，仍然可以编辑命令，仍然会重新做风险检测。

## CLI 单次命令

除了交互模式，也可以直接调用 CLI：

```bash
python -m app.cli generate "查看 8080 端口被谁占用"
python -m app.cli explain 'find . -name "*.py" | wc -l'
python -m app.cli check "rm -rf /"
python -m app.cli highlights
```

需要 JSON 输出时添加 `--json`：

```bash
python -m app.cli check "rm -rf /" --json
```

## 可选 API

项目保留 FastAPI 接口，便于课程展示或外部系统调用，但这不是主要使用方式。

启动：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

接口：

- `GET /health`
- `POST /api/shell/generate`
- `POST /api/shell/explain`
- `POST /api/shell/check`
- `GET /api/shell/history/highlights`

## 总体架构

项目按“终端交互层 + 服务层 + LLM 接入层 + skills 层 + 安全规则层 + 本地存储层”组织。

主要文件：

- `shellgpt.py`：Linux 终端交互入口，负责读取用户输入、展示候选命令、准备执行、调用 shell 执行命令。
- `app/services/command_service.py`：自然语言转命令主流程，负责召回 skills、构造 prompt、调用 LLM、合并安全检查结果。
- `app/llm/minimax_client.py`：MiniMax Anthropic-compatible Messages API 调用封装，负责请求、重试、响应文本提取和 JSON 解析。
- `app/skills/nl2bash_skills.py`：手工整理的 NL2Bash 风格技能库，覆盖文件查找、文本处理、进程、网络、权限、压缩、包管理等任务。
- `app/skills/skill_loader.py`：极简关键词召回逻辑，根据用户 query 选出相关 skills 注入 prompt。
- `app/services/safety_service.py`：本地危险命令规则识别，不依赖大模型。
- `app/services/history_service.py`：本地 JSON 历史记录，保存最近命令并支持复刻。
- `app/main.py`：FastAPI 可选接口入口。
- `app/cli.py`：CLI 单次命令入口。

这种结构的重点是简单可运行：没有数据库、没有前端页面、没有向量库、没有 LangChain/LlamaIndex，也没有训练流程。

## 主流程原理

一次完整的终端交互流程如下：

1. 用户输入中文或英文需求。
2. `skill_loader.py` 用关键词匹配从 NL2Bash skills 中召回相关技能。
3. `prompts.py` 将用户需求、系统约束、相关 skills 拼成提示词。
4. `MiniMaxClient.generate_json()` 调用 MiniMax-M2.7。
5. 如果 LLM 成功返回 JSON，使用模型生成的主命令、候选命令、解释和风险说明。
6. 如果 LLM 网络失败、服务过载或输出不是 JSON，程序自动走本地 skills fallback。
7. `safety_service.py` 对候选命令做本地规则安全检查。
8. 用户选择命令编号。
9. `shellgpt.py` 把所选命令预填到输入框，用户可直接编辑。
10. 执行前再次调用 `safety_service.py` 检查最终命令。
11. `low` 风险直接执行，`medium` 风险要求输入 `yes`，`high` 风险拒绝执行。
12. 命令通过 `subprocess.run(command, shell=True)` 在当前终端执行。
13. 成功时只显示命令输出，失败时显示非 0 退出码。
14. 执行过的命令写入 `app/storage/history.json`，供 `:history` 复刻。

这个流程让 LLM 负责理解和生成，让规则负责安全底线，让用户在执行前保留最终控制权。

## MiniMax Anthropic-Compatible API 接入

项目使用 MiniMax 的 Anthropic-compatible Messages API，不使用 OpenAI `/chat/completions` 格式。

配置：

```env
LLM_BASE_URL=https://api.minimaxi.com/anthropic
LLM_MODEL=MiniMax-M2.7
```

实际请求地址由客户端自动拼成：

```text
https://api.minimaxi.com/anthropic/v1/messages
```

请求头使用：

```text
x-api-key: <LLM_API_KEY>
anthropic-version: 2023-06-01
content-type: application/json
```

请求体核心字段：

```json
{
  "model": "MiniMax-M2.7",
  "max_tokens": 2048,
  "temperature": 0.1,
  "system": "系统提示词",
  "messages": [
    {"role": "user", "content": "用户任务提示词"}
  ]
}
```

响应解析方式：

- MiniMax Anthropic-compatible API 返回 `content` blocks。
- 程序遍历 `content[]`，提取其中 `type == "text"` 的 `text` 字段。
- 提取出的文本再交给 JSON 解析器。
- 如果模型输出了 Markdown 代码块，解析器会先做轻量清理。
- 如果仍不是合法 JSON，会进行一次纠正提示。

重试策略：

- 对 `429`、`500`、`502`、`503`、`504`、`529` 做有限退避重试。
- 网络错误和可重试 HTTP 错误不会直接污染终端输出。
- 如果最终仍失败，上层服务会走本地 skills fallback。

## NL2Bash skills 机制

本项目没有训练模型，也没有下载大型数据集。这里的“NL2Bash skills”是把 NL2Bash 类数据集中常见的自然语言到命令模式，手工整理成小型技能库。

每条 skill 包含：

- `category`：任务类别，例如文件查找、文本处理、网络排查。
- `intent`：任务意图，例如“按扩展名查找文件”。
- `patterns`：关键词和短语，用于召回。
- `command_templates`：典型命令模板。
- `tips`：生成时应该注意的规则。

示例：

```python
{
    "category": "file_search",
    "intent": "按文件名或扩展名查找文件",
    "patterns": ["查找", "找文件", "扩展名", "pdf", "find file"],
    "command_templates": ["find . -type f -name '<pattern>'"],
    "tips": ["递归查找优先使用 find", "通配符建议用引号包裹"]
}
```

召回方式很简单：

1. 将用户 query 转成小写。
2. 与 skill 的 `patterns`、`intent`、`category` 做关键词匹配。
3. 取最相关的若干条 skill。
4. 拼进 LLM prompt，指导模型生成更稳定的 Shell 命令。

这样设计的好处是成本低、结构清楚、容易解释，适合课程实验和原型系统。缺点是覆盖范围受手工 skills 限制，不如真正的检索系统全面。

## 本地 fallback 机制

LLM 不可用时，程序不会直接报错退出，而是尝试使用本地 skills fallback。

例如：

- “查找当前目录下所有 pdf 文件” fallback 为：
  ```bash
  find . -type f -name '*.pdf'
  ```
- “查看 8080 端口被谁占用” fallback 为：
  ```bash
  lsof -i :8080
  ```
- “统计 logs 目录下包含 error 的行数” fallback 为：
  ```bash
  grep -R "error" logs | wc -l
  ```

fallback 的目标不是覆盖所有自然语言需求，而是在没有网络、MiniMax 服务过载、API Key 未配置时，保证常见演示场景仍然可用。

## 安全策略

安全判断优先走本地规则，不依赖 LLM。原因是危险命令识别属于稳定性要求很高的逻辑，不能完全交给概率模型。

风险等级：

- `low`：只读或低影响命令，例如 `find`、`grep`、`ls`。
- `medium`：可能影响系统或文件的命令，例如普通 `rm -rf`、`kill -9`、`sed -i`、`iptables`。
- `high`：高风险命令，例如删除根目录、格式化磁盘、关机重启、下载脚本直接执行。

高风险示例：

```text
rm -rf /
风险等级: high
高风险命令已被拒绝执行。
```

当前覆盖的典型危险模式包括：

- `rm -rf /`
- `rm -rf /*`
- `mkfs`
- `dd if=... of=/dev/...`
- `shutdown`
- `reboot`
- `init 0`
- `poweroff`
- `chmod -R 777 /`
- `chown -R`
- `curl ... | sh`
- `wget ... | sh`
- 重定向写入 `/etc/...`
- `find ... -delete`
- `xargs rm`

执行策略：

- `low` 风险：可直接执行。
- `medium` 风险：需要输入 `yes` 二次确认。
- `high` 风险：默认拒绝执行，第一版不提供强制执行开关。

## 准备执行阶段

用户选择候选命令后，不会立即执行。程序会进入准备执行阶段：

```text
准备执行，Enter 执行，可直接编辑命令:
> find . -type f -name '*.pdf'
```

实现方式：

- Linux 下使用标准库 `readline`。
- 通过 `readline.set_pre_input_hook()` 将命令插入到输入框。
- 用户可以像编辑普通终端命令一样修改内容。
- 如果环境不支持 `readline`，程序会降级为打印默认命令并允许输入替代命令。

行为规则：

- 直接 Enter：执行输入框中的命令。
- 修改后 Enter：执行修改后的命令。
- 输入 `n` 或 `no`：取消。
- 输入 `q`、`:q`、`:quit`：退出。
- 删除成空内容：取消。

最终命令会重新进行安全检查，因此用户手动修改命令也不会绕过风险检测。

## 历史记录与复刻

历史记录保存在本地 JSON 文件：

```text
app/storage/history.json
```

当前策略：

- 只保留最近 10 条记录。
- `:history` 面向用户只展示具体命令，不展示类型、分类或统计摘要。
- 历史命令去重展示，最新的排在最前面。
- 选择历史命令后进入同一个准备执行阶段，可以再次编辑。

示例：

```text
请输入需求: :history

最近命令:
[1] find . -type f -name '*.pdf'
[2] lsof -i :8080

输入编号复刻执行，输入 n 返回: 1

准备执行，Enter 执行，可直接编辑命令:
> find . -type f -name '*.pdf'
```

这样设计的原因是：用户真正需要复用的是“具体命令”，而不是历史统计报表。

## 设计取舍

本项目选择“规则约束 + LLM 生成 + NL2Bash skills + 终端人工确认”的混合方案。

为什么不只用规则：

- 纯规则很难覆盖自然语言表达。
- 例如“找出最近修改过的 PDF”可以有多种说法，规则写多了会变复杂。

为什么不只用 LLM：

- LLM 可能生成危险命令。
- LLM 可能输出格式不稳定。
- LLM 网络不可用时会影响主流程。

为什么不训练模型：

- 训练成本高。
- 数据准备复杂。
- 项目目标是课程实验和原型系统，不需要训练流程。

为什么不用数据库：

- 历史只需要最近 10 条命令。
- JSON 文件足够简单可控。

为什么不用复杂前端：

- 目标用户在 Linux 终端中工作。
- 命令助手应该尽量贴近终端工作流。

## 限制

- 当前主要面向 Bash/Linux，不保证兼容 PowerShell、fish、zsh 的所有语法差异。
- 命令解释没有实现完整 Shell AST，只做常见命令和 LLM 辅助解释。
- skills 是手工整理的小型库，不能覆盖所有命令场景。
- MiniMax 服务过载或网络不可用时，复杂需求会降级为 fallback，生成能力会变弱。
- 高风险命令默认拒绝执行，不提供强制执行入口。

## 最小验证

启动：

```bash
python shellgpt.py
```

输入：

```text
查找当前目录下所有 pdf 文件
```

预期：

```text
推荐命令:
[1] find . -type f -name '*.pdf'
    风险等级: low
```

选择 `1` 后：

```text
准备执行，Enter 执行，可直接编辑命令:
> find . -type f -name '*.pdf'
```

验证历史：

```text
:history
```

预期显示最近 10 条具体命令，并可输入编号复刻。

验证高风险：

```text
rm -rf /
```

预期：

```text
风险等级: high
高风险命令已被拒绝执行。
```

## 项目适用场景

本项目适合作为：

- Linux 终端智能助手原型。
- LLM + 规则系统的课程实验。
- NL2Bash skills 提示工程示例。
- 命令安全检测与人机确认流程演示。

它的重点不是覆盖所有 Shell 功能，而是在最少依赖和最少架构复杂度下，跑通一个完整、可解释、可演示的智能 Shell 命令助手。
