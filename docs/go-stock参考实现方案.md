# go-stock 参考功能实现方案

> 参考 [go-stock](https://github.com/ArvinLovegood/go-stock) 在 ROX Quant 3.0 中落地的实现计划：多模型配置、AI 模板、条件选股+AI 总结。  
> 文档与代码同步更新。

---

## 一、多模型 / 多平台配置

### 1.1 目标

- 支持多个 AI 后端（DeepSeek、OpenAI、Ollama、硅基流动、火山方舟等），通过「当前使用哪个」切换，无需改代码。
- 配置来源：环境变量 + 可选「当前选用 provider」设置（存 DB 或 .env）。

### 1.2 配置结构（环境变量）

在 `.env` / `app/core/config.py` 中扩展：

```text
# 当前使用的 AI 后端（与下表中的 key 一致）
AI_PROVIDER=deepseek

# 多后端定义（可选，未配置则用默认 AI_API_KEY + AI_BASE_URL）
# 格式：AI_PROVIDERS='{"deepseek":{"base_url":"https://api.deepseek.com","api_key_env":"AI_API_KEY","default_model":"deepseek-chat"},"openai":{"base_url":"https://api.openai.com/v1","api_key_env":"OPENAI_API_KEY","default_model":"gpt-4o-mini"}}'
```

或每个后端单独写（便于维护）：

```text
# DeepSeek
AI_API_KEY=sk-xxx
AI_BASE_URL=https://api.deepseek.com

# OpenAI（可选）
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1

# 硅基流动（可选）
SILICONFLOW_API_KEY=xxx
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
```

### 1.3 涉及文件与改动

| 文件 | 改动 |
|------|------|
| `app/core/config.py` | 增加 `AI_PROVIDER`、`AI_PROVIDERS`（或从 env 解析多后端列表）。 |
| `app/rox_quant/llm.py` | `AIClient` 根据 `AI_PROVIDER` 和 `AI_PROVIDERS` 构建多个 client；对外提供 `get_client(provider=None)`、`list_providers()`。 |
| `app/api/endpoints/ai.py` | 新增 `GET /api/ai/providers` 返回可用后端列表；`POST /api/ai/chat`、`/analyze` 请求体增加 `provider?: string`、`model?: string`。 |
| `.env.example` | 增加多后端示例与 `AI_PROVIDER` 说明。 |

### 1.4 API 约定

- `GET /api/ai/providers`  
  - 返回：`{ "current": "deepseek", "list": [ { "id": "deepseek", "name": "DeepSeek", "default_model": "deepseek-chat", "available": true } ] }`  
  - `available` 可通过对 base_url 做一次 head 或轻量请求判断（可选）。
- `POST /api/ai/chat` 请求体增加：`provider?: string`、`model?: string`，缺省用 config 的当前 provider 与默认 model。

---

## 二、可配置 AI 分析 / 选股模板

### 2.1 目标

- 用户可选择/编辑「分析用提示词模板」（如：技术面优先、基本面优先、短线/长线）。
- 模板用于：个股分析、市场简报、选股总结等，与具体接口绑定（如 template_id 或 template_key）。

### 2.2 存储

- 表 `prompt_templates`：`id, user_id, name, key, content, scope, created_at`。  
  - `key`：如 `stock_analysis`、`market_briefing`、`screen_summary`。  
  - `scope`：`system`（内置，不可删）/ `user`（用户自定义）。  
- 或内置模板放 JSON 文件，用户自定义存 DB；接口层统一「按 key + 可选 user_id」解析。

### 2.3 涉及文件与改动

| 文件 | 改动 |
|------|------|
| `app/db.py` | 增加 `prompt_templates` 表；`get_prompt_template(key, user_id=None)`、`list_prompt_templates(scope=...)`。 |
| `app/rox_quant/llm.py` | `analyze_stock`、`generate_market_briefing` 等支持传入 `system_prompt_override` 或 `template_key`，从 DB/JSON 读模板内容。 |
| `app/api/endpoints/ai.py` | `GET /api/ai/templates` 返回模板列表；`GET /api/ai/templates/{key}` 返回单个；`POST /api/ai/templates` 新建/更新用户模板；chat/analyze 请求体增加 `template_id` 或 `template_key`。 |

### 2.4 API 约定

- `GET /api/ai/templates?scope=system|user`  
  - 返回：`{ "items": [ { "id", "name", "key", "scope", "preview" } ] }`  
- `GET /api/ai/templates/{key}`  
  - 返回：`{ "key", "name", "content", "scope" }`  
- `POST /api/ai/templates`  
  - body：`{ "name", "key", "content", "scope": "user" }`  
- 使用：在 `POST /api/ai/chat`、`/analyze` 中增加 `template_key`，若存在则用该模板覆盖默认 system prompt 或拼接进 context。

---

## 三、条件选股 + AI 总结

### 3.1 目标

- 先按现有条件选股（如寻龙诀、指标筛选）得到列表，再调用 AI 对列表做「一句话总结 + 关注建议」，形成闭环。

### 3.2 接口设计

- `POST /api/strategy/screen-with-ai`  
  - body：`{ "screen_type": "xunlongjue" | "custom", "params": { ... }, "max_results": 20 }`  
  - 内部：调用现有 `api_screen_xunlongjue` 或通用筛选，得到 `items`；将 `items` 拼成文本，调用 `AIClient.chat_with_search` 或专用方法，传入「选股结果摘要」模板，得到 AI 总结。  
  - 返回：`{ "items": [...], "total": N, "ai_summary": "..." }`  

### 3.3 涉及文件与改动

| 文件 | 改动 |
|------|------|
| `app/api/endpoints/strategy.py` | 新增 `screen_with_ai`；内部调选股逻辑 + `AIClient` 生成总结。 |
| `app/rox_quant/llm.py` | 可选：新增 `summarize_screen_results(items, template_key=None)`，内部用固定或模板提示词。 |
| 前端（专业版/经典版） | 选股结果页增加「AI 总结」区块，请求 `screen-with-ai` 或先选股再单独调 `POST /api/ai/summarize-screen`（若拆成两段）。 |

### 3.4 API 约定

- `POST /api/strategy/screen-with-ai`  
  - 请求：`{ "screen_type": "xunlongjue", "params": { "codes": "", "max_codes": 30 }, "max_results": 20, "provider": "deepseek", "model": "deepseek-chat" }`  
  - 响应：`{ "items": [ { "code", "name", "reason", "detail" } ], "total": N, "ai_summary": "本批共 N 只，建议重点关注..." }`  

---

## 四、实施顺序建议

1. **Phase 1**：多模型配置（config + llm + GET /api/ai/providers + chat/analyze 支持 provider/model）。 ✅ 已实现  
2. **Phase 2**：AI 模板（DB 表 + GET/POST /api/ai/templates + chat/analyze 支持 template_key）。 ✅ 已实现（模板 CRUD；chat/analyze 使用 template_key 可选后续接入）  
3. **Phase 3**：条件选股 + AI 总结（POST /api/strategy/screen-with-ai + 前端选股页「AI 总结」）。 ✅ 已实现  

---

## 五、已实现 API 一览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/ai/providers | 返回当前 AI 后端与可用列表（current, list[{ id, name, default_model, available }]） |
| POST | /api/ai/chat | body 增加 provider?, model?；缺省用当前配置 |
| POST | /api/ai/analyze | body 增加 provider?, model? |
| GET | /api/ai/templates | 查询参数 scope?；返回模板列表（需登录） |
| GET | /api/ai/templates/{key} | 按 key 获取单个模板内容（需登录） |
| POST | /api/ai/templates | body: name, key, content, scope；新建用户模板（需登录） |
| POST | /api/strategy/screen-with-ai | body: screen_type, params?, max_results?, provider?, model?；返回 items, total, ai_summary |

---

## 六、与 go-stock 的对应关系

| go-stock 能力 | ROX 实现方式 |
|---------------|--------------|
| 多模型/平台切换 | AI_PROVIDER + AI_PROVIDERS + GET /api/ai/providers |
| 可配置提问模板 | prompt_templates + /api/ai/templates + template_key 入参 |
| AI 智能选股 | screen-with-ai = 现有选股 + AI 总结 |
| 市场/个股情绪 | 后续可加情绪指标接口 + 模板中「情绪」段落（本方案不展开） |
| 涨跌报警 | 后续可加 condition_orders 触发 + 通知渠道（本方案不展开） |

文档随代码更新；完成 Phase 1/2/3 后在本文件中更新「状态」与「已实现 API」列表。
