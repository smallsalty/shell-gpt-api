# Shell-GPT Minimal Command Assistant

一个最小可运行的类 shell-gpt 智能 Shell 命令助手，支持自然语言生成命令、命令解释、危险命令检测和历史亮点总结。

## 安装

```powershell
cd D:\firstmoney\shell-gpt\shell_assistant
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

复制环境变量示例并填写 MiniMax API Key：

```powershell
Copy-Item .env.example .env
```

`.env` 示例：

```env
LLM_API_KEY=your_key
LLM_BASE_URL=https://api.minimax.io/v1
LLM_MODEL=MiniMax-M2.7
```

默认按 OpenAI 兼容的 `POST {LLM_BASE_URL}/chat/completions` 调用。如果账号使用的 MiniMax 网关路径不同，只需要调整 `LLM_BASE_URL`。

## 运行 API

```powershell
cd D:\firstmoney\shell-gpt\shell_assistant
uvicorn app.main:app --reload
```

接口：

- `GET /health`
- `POST /api/shell/generate`
- `POST /api/shell/explain`
- `POST /api/shell/check`
- `GET /api/shell/history/highlights`

生成命令示例：

```powershell
curl -X POST http://127.0.0.1:8000/api/shell/generate `
  -H "Content-Type: application/json" `
  -d "{\"query\":\"查找当前目录下所有 pdf 文件\",\"shell_type\":\"bash\",\"os\":\"linux\",\"context\":\"\"}"
```

## 运行 CLI

```powershell
cd D:\firstmoney\shell-gpt\shell_assistant
python -m app.cli generate "查找当前目录下所有 pdf 文件"
python -m app.cli explain "find . -name `"*.py`" | wc -l"
python -m app.cli check "rm -rf /"
python -m app.cli highlights
```

需要机器可读输出时添加 `--json`：

```powershell
python -m app.cli check "rm -rf /" --json
```

## 验证场景

```powershell
python -m app.cli generate "查找当前目录下所有 pdf 文件" --json
python -m app.cli generate "查看 8080 端口被谁占用" --json
python -m app.cli generate "统计 logs 目录下包含 error 的行数" --json
python -m app.cli generate "删除当前目录所有临时文件" --json
python -m app.cli check "rm -rf /tmp/test" --json
python -m app.cli check "rm -rf /" --json
python -m app.cli explain "find . -name `"*.py`" | wc -l" --json
python -m app.cli highlights --json
```

未配置 `LLM_API_KEY` 时，生成命令会使用内置 skills 模板做有限 fallback；配置 API Key 后，会使用 MiniMax-M2.7 生成更灵活的结果。

## 实现原理

本系统采用“规则约束 + LLM 生成 + NL2Bash 技能提示”的混合方案。

规则层用于危险命令识别，对 `rm -rf /`、`mkfs`、`dd of=/dev/...`、`curl | sh`、关机重启、递归权限修改、写入 `/etc` 等高风险操作做稳定提醒。这样可以弥补纯大模型在安全判断上的不稳定。

skills 层将 NL2Bash 等数据集中的常见任务模式总结为“任务类别 + 命令模板 + 使用提示”，覆盖文件查找、文本处理、进程系统、网络排查、权限用户、压缩归档、包管理等场景。生成命令前会用关键词匹配召回相关 skills，并注入提示词。

LLM 层使用 MiniMax-M2.7 完成自然语言理解、命令生成、命令解释和摘要，要求输出统一 JSON，便于 API 和 CLI 处理。若模型输出不是 JSON，会进行一次轻量纠正和提取。

历史亮点层将最近记录保存在本地 `app/storage/history.json`，通过简单规则统计常见类别、高频命令模式和高风险命令数量。

这样设计比纯规则更灵活，比纯大模型更稳定，也比训练专用模型更省成本、实现更快，适合作为课程实验和原型系统。

## 合理取舍

- 只做 Bash/Linux 主路径，不实现完整 Shell AST。
- skills 检索使用关键词匹配，不引入向量库或 RAG 框架。
- history 使用本地 JSON 文件，不引入数据库。
- 命令解释采用常见命令规则 + LLM 补充，不追求覆盖所有 Shell 语法。
- 不提供前端页面、用户系统、队列、Docker 编排或大规模测试框架。

