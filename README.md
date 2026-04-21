# Shell-GPT Linux 终端助手

一个最小可运行的 Shell 命令助手，面向 Linux 终端使用。用户输入中文或英文需求后，程序生成候选 Shell 命令；用户选择后，程序在当前终端执行命令，并在执行前显示风险等级和安全提示。

项目重点是命令行交互，不需要打开网站或浏览器。

## 安装

```bash
cd /path/to/shell-gpt
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

编辑 `.env`，填写 MiniMax API Key：

```env
LLM_API_KEY=your_key
LLM_BASE_URL=https://api.minimax.io/v1
LLM_MODEL=MiniMax-M2.7
```

未配置 `LLM_API_KEY` 时，程序仍会使用内置 skills fallback 生成部分常见命令。

## 终端交互运行

推荐入口：

```bash
python shellgpt.py
```

也可以通过 CLI 子命令启动：

```bash
python -m app.cli interactive
```

启动后输入中文需求：

```text
请输入需求: 查找当前目录下所有 pdf 文件
```

程序会输出候选命令、解释和风险信息：

```text
推荐命令:
[1] find . -type f -name '*.pdf'
    风险等级: low

解释:
在当前目录及子目录中查找所有 PDF 文件。

风险等级: low
输入编号执行，输入 n 跳过，输入 q 退出:
```

输入编号后，程序会在当前终端执行命令，并显示命令输出和退出码。

## 交互指令

```text
:help     查看帮助
:history  查看历史亮点
:q        退出
:quit     退出
```

## CLI 单次命令

除了交互模式，也可以直接使用原有 CLI：

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

## 安全策略

- `low` 风险命令：用户输入编号后执行。
- `medium` 风险命令：用户输入编号后，必须再输入 `yes` 才执行。
- `high` 风险命令：默认拒绝执行，只展示风险原因和安全建议。

危险命令识别优先走本地规则，不依赖大模型。规则覆盖 `rm -rf /`、`mkfs`、`dd of=/dev/...`、`shutdown`、`reboot`、`chmod -R 777 /`、`curl | sh`、写入 `/etc` 等常见高风险模式。

## 可选 API

项目仍保留 FastAPI 能力，但不是主要使用方式：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

接口包括：

- `GET /health`
- `POST /api/shell/generate`
- `POST /api/shell/explain`
- `POST /api/shell/check`
- `GET /api/shell/history/highlights`

## 实现原理

本系统采用“规则约束 + LLM 生成 + NL2Bash 技能提示”的混合方案：

- 规则层负责危险命令识别，保证高风险命令能被稳定拦截。
- skills 层将 NL2Bash 常见任务模式整理成任务类别、命令模板和使用提示。
- LLM 层使用 MiniMax-M2.7 完成自然语言理解、命令生成和命令解释。
- 历史亮点层使用本地 `app/storage/history.json` 记录最近请求和命令，做简单统计。

这种方式比纯规则更灵活，比纯大模型更稳定，也比训练专用模型更省成本，适合作为课程实验和原型系统。

## 最小验证

在 Linux 终端中运行：

```bash
python shellgpt.py
```

依次输入：

```text
查找当前目录下所有 pdf 文件
查看 8080 端口被谁占用
rm -rf /
```

预期前两个请求能生成命令并允许选择执行，`rm -rf /` 会被识别为高风险并拒绝执行。
