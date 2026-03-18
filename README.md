# Happy Agent 脚手架

一个面向新手的 Agent 后端起步仓库（当前是最小可运行版本）。

## 当前能力（2026-03-18）

- `GET /health`：健康检查
- `GET /tools`：查看可用工具
- `POST /chat`：最小 Agent 闭环（读消息 -> 规划工具 -> 执行 -> 汇总）

内置工具：

- `get_server_time`
- `calculator`（安全 AST 计算）

## 目录结构（职责分离）

```text
apps/api/app/
├─ main.py                # 应用入口，只创建 FastAPI + 挂路由
├─ routes/
│  └─ router.py           # HTTP 路由层
├─ schemas/
│  └─ chat.py             # 请求/响应模型
├─ tools/
│  ├─ time_tool.py        # 时间工具
│  ├─ calculator.py       # 计算器工具
│  └─ registry.py         # 工具注册中心（含参数校验）
└─ agent/
   ├─ planner.py          # 工具规划（显式 + 启发式）
   ├─ executor.py         # 工具执行（归一化 + 校验 + 调用）
   └─ service.py          # 编排流程
```

## Tool 逻辑（已补齐）

现在有两种触发方式：

1. 启发式触发（自动）
- 例：`what time is it and 2+2`
- 会自动触发 `get_server_time` + `calculator`

2. 显式触发（推荐调试）
- 语法：`/tool <tool_name> <payload>`
- 示例：
  - `/tool get_server_time`
  - `/tool calculator 12*(3+5)`
  - `/tool calculator {"expression":"12*(3+5)"}`

参数规则：

- 先做参数归一化（calculator 支持 `expr/formula/input/text` 别名）
- 再做 schema 校验（必填、类型、未知参数）
- 校验失败时，会在 `tool_calls[].error` 里返回清晰错误

## DeepSeek 调用逻辑（优先）

`POST /chat` 现在会优先调用 DeepSeek：

1. 先让 DeepSeek 决定是否要调用工具（以及参数）。
2. 如果有工具调用，就执行工具，再让 DeepSeek基于工具结果生成最终回答。
3. 如果不需要工具，DeepSeek会直接回答，不会只返回工具提示。
4. 如果 DeepSeek 不可用或调用失败，自动回退到本地启发式 tool 流程。

说明：
- 无工具场景下，系统会发起“直接回答”调用，不复用规划阶段的模板回答。

需要的环境变量：

- `OPENAI_API_KEY`：DeepSeek API Key
- `OPENAI_BASE_URL`：默认 `https://api.deepseek.com`
- `OPENAI_CHAT_MODEL`：建议 `deepseek-chat`
- `DEBUG_LLM`：可选，设为 `true/1` 会输出 LLM 路径调试日志

## 请求处理流程

`POST /chat` 的核心流程：

1. 在 `agent/service.py` 读取最后一条 user 消息
2. 在 `agent/planner.py` 生成工具计划
3. 在 `agent/executor.py` 执行工具
4. 在 `agent/service.py` 汇总为 `ChatResponse`

## 本地启动（不使用 Docker）

```bash
cd apps/api
uv venv .venv
# PowerShell
.venv\Scripts\Activate.ps1
# macOS/Linux
# source .venv/bin/activate
uv pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动后访问：

- `http://localhost:8000/docs`
- `http://localhost:8000/health`

## 最小调用示例

### 1) health

```bash
curl http://localhost:8000/health
```

### 2) tools

```bash
curl http://localhost:8000/tools
```

### 3) chat（自动触发）

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"what time is it and 12*(3+5)"}],"use_tools":true,"max_tool_calls":3}'
```

### 4) chat（显式触发）

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"/tool calculator 12*(3+5)"}],"use_tools":true}'
```

排错提示：

- `messages[].role` 只支持：`system`、`user`、`assistant`
- 如果想触发计算工具，`content` 里要有算式（如 `2+1`）或使用 `/tool calculator ...`
- 响应里的 `llm_used` 表示本次是否实际走了 DeepSeek 路径

## 给你的阅读顺序（新手建议）

1. 先看 `apps/api/app/main.py`
2. 再看 `apps/api/app/routes/router.py`
3. 再看 `apps/api/app/agent/service.py`
4. 然后看 `apps/api/app/agent/planner.py` 和 `apps/api/app/agent/executor.py`
5. 最后看 `apps/api/app/tools/registry.py`

## 协作约定

- 每次代码改动后同步更新 `README.md`
- 每次代码改动后新建或更新 `CHANGELOG.md`
