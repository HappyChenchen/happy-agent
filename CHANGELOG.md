# 更新日志

本文件记录本项目的所有重要变更。

格式参考 Keep a Changelog，当前按日期追踪变更。

## [Unreleased]

### 新增

- 在 `apps/api/app/main.py` 中加入行内说明注释与模块流程 docstring。
- 新增 `ToolCallPlan` 模型，使工具规划结构更明确。
- 新增模块化目录与文件，进一步清晰职责边界：
  - `app/routes/router.py`
  - `app/schemas/chat.py`
  - `app/tools/{time_tool.py,calculator.py,registry.py}`
  - `app/agent/{planner.py,executor.py,service.py}`
- 在各 Python 模块加入中文顶层注释，提升新手可读性。
- 在 planner 中增加显式工具调用语法：`/tool <name> <payload>`（同时支持 `tool:` 和 `调用` 前缀）。
- 在 registry/executor 中加入工具参数标准化与校验。
- 新增 `app/agent/deepseek_client.py`，用于兼容 OpenAI 接口的 DeepSeek API 调用。

### 变更

- 文档更新与代码变更保持同步（`README.md` + `CHANGELOG.md`）。
- `POST /chat` 现支持 `max_tool_calls`（默认 `3`，范围 `0..10`）作为单次请求的安全上限。
- 将 planner 函数重命名为 `_plan_tool_calls_heuristic()`，语义更清晰。
- `main.py` 精简为仅负责应用启动（加载 env + 创建 app + 挂载 router）。
- Agent 工作流迁移到 service/planner/executor 模块。
- 重写 `README.md`，补充新目录职责和新手阅读顺序。
- 将路由目录从 `app/api` 重命名为 `app/routes`，避免命名重复。
- `service.py` 在未执行工具时改为返回更实用的提示文本。
- `README.md` 增加显式工具调用与参数校验行为说明。
- 修复 `service.py` 中 `_last_user_message` 的判断条件，确保正确识别用户消息。
- 将 `ChatMessage.role` 限制恢复为 `system|user|assistant`。
- `POST /chat` 现在优先走 DeepSeek 进行规划/回答，并可按需调用工具。
- 新增自动降级：当 DeepSeek 不可用或报错时，回退到本地启发式工具流程。
- 新增 `DEBUG_LLM` 开关，用于记录 `/chat` 使用 DeepSeek 还是回退路径。
- 在 `/chat` 响应中新增 `llm_used` 字段，标识是否走了 LLM 路径。
- 优化 DeepSeek 的无工具分支：直接回答问题，不再只返回工具建议。
- 确保无工具响应始终使用专用 direct-answer 调用（避免返回 planner 模板化回复）。

## [2026-03-18]

### 新增

- 在 `apps/api/app/main.py` 新增最小可运行的 agent API 骨架。
- 新增 `POST /chat` 接口，提供基础工具规划与执行流程。
- 新增 `GET /tools` 接口，用于工具发现。
- 内置工具：
  - `get_server_time`
  - `calculator` (safe AST-based expression evaluation)

### 变更

- 更新 `README.md`，同步当前接口、启动方式与 API 调用示例。
