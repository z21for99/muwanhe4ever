# 沐婉荷角色运行时 — 设计文档

- 日期：2026-10-24
- 状态：Approved（2026-10-26），进入实现计划
- 源文本：`花嫁(2).txt`（1,082,507 字，四卷；源文件顺序 窃脂→拾棘→阴雷→洊雷，正确阅读顺序 阴雷→窃脂→拾棘→洊雷）
- 仓库：`muwanhe4ever`（当前 private）
- 范围：v1 本地优先、纯文字的角色运行时；语音/立绘不做，只留接口

---

## 1. 背景与目标

原著《花嫁》当前文本 1,082,507 字，四卷（窃脂 / 拾棘 / 阴雷 / 洊雷），第一人称白风远视角，接近完结（第四卷末尾是否最终结局待确认）。源文件把前三卷顺序排成 窃脂→拾棘→阴雷，并新增第四卷 洊雷；正确阅读顺序是 阴雷→窃脂→拾棘→洊雷，编译器按 `volume_order` 重排，不依赖文件顺序，且必须抽 `story_time`。目标不是做一个“会聊天的角色卡”，而是做一个**角色运行时**：把原著编译成可检索、可推理、可评测的记忆与人格结构，让沐婉荷在**最新连载进度**上，以她自己的心理、语言和关系逻辑，与扮演白风远的用户对话。

成功标准不是“回答像”，而是：

- 遇到原著里没有的新情境，她的反应仍然像她；
- 她记得自己经历过什么，也知道自己**不该**知道什么；
- 她对白风远的反应，能从原著关系里找到依据；
- 换一个用户、换一台机器，仍然能复现同一个角色。

## 2. 非目标

- 不做 18+ 内容：亲密场景只保留 fade-to-black 的关系与心理后果，不生成露骨描写。
- 不做多用户托管服务：每个用户本地跑自己的实例。
- v1 不做语音、立绘、Live2D、主动消息。
- v1 不做模型微调：先靠记忆检索 + style bank + prompt 约束。
- 公开仓库不包含原著文本、角色包、向量索引。

## 3. 核心设计决策

| 决策 | 选择 | 理由 |
|---|---|---|
| 部署形态 | 本地单体 + 可插拔 provider | 安装简单，同时给开源用户换后端的口子 |
| 对话“现在” | 最新连载进度 | 角色知道截至当前文本的一切，未来未知 |
| 用户身份 | canon 白风远 | 她把你当“她儿子”，canon 记忆共享 |
| 记忆分层 | canon / inferred / style / personal | 把“事实”“推断”“口吻”“你和她的事”分开 |
| 人设表达 | 情境化 style bank | 单一 voice anchor 会把角色压扁 |
| 编排 | LangGraph runtime；编译器和 schema 不依赖 LangChain | 用状态图/checkpoint，但不让框架定义叙事结构 |
| 向量 | 默认 LanceDB；`VectorStore` 接口可换 Qdrant local | 本地零服务，后期可换 |
| 接口 | OpenAI 兼容 `/v1/chat/completions` | IM 生态事实标准，用户自己接 |

## 4. 数据模型

SQLite 为事实源；向量索引另存。所有 canon 数据带 `canon_version`，支持增量编译。

### 4.1 表

| 表 | 关键字段 | 说明 |
|---|---|---|
| `characters` | `id, name, aliases, role, description` | 角色表；别名/称谓归一 |
| `scenes` | `id, volume, chapter, scene_index, story_time, location, pov, present, summary, text_span, source_hash` | 场景卡，最小检索单元 |
| `utterances` | `id, scene_id, speaker_id, addressee_id, text, context, emotion, intent, scene_type, power, markedness, explicitness, tags` | 她/他人的原话 + 情境标签 |
| `facts` | `id, s, p, o, cause, valid_from, valid_to, visible_to, layer, confidence, source_scene` | SPOCV + 可见性 + 时间 |
| `events` | `id, scene_id, participants, action, cause, consequence, story_time, layer, confidence, source_span` | 事件图节点 |
| `relationships` | `id, from_id, to_id, dimension, value, valid_from, evidence` | 多维关系状态 |
| `arc_points` | `id, volume, chapter, values, goals, relationships, state_summary` | 角色弧锚点 |
| `style_modes` | `id, name, addressee, scene_type, emotion, intent, description, syntax, forbidden` | 情境口吻模式 |
| `style_samples` | `id, mode_id, utterance_id, text, context, markedness` | 原话 exemplar |
| `personal_memory` | `id, user_id, session_id, turn_id, ts, summary, emotion, relationship_delta, source` | 你和她的对话记忆 |
| `canon_versions` | `id, source_path, source_hash, compiled_at, stats` | 编译版本 |
| `compile_runs` | `id, canon_version, stage, status, stats` | 断点续跑/审计 |
| `eval_items` | `id, type, prompt, rubric, weight, expected` | 评测集 |

### 4.2 两层证据

- **canon**：原文可直接支持的事实/原话/事件，`confidence=1.0`，带 `source_scene`。
- **inferred**：动机、秘密、防御机制、独处心理；`confidence` + `evidence[]`，允许作者审核修正。
- 运行时她按 inferred 层“活”，但系统知道哪些是原著、哪些是重构。

### 4.3 可见性与内容策略

- `facts.visible_to`：只有她经历过、看到、被告知、或属于公共常识的事实才可见。
- `explicitness`：`safe | fade_to_black | explicit`；编译器把 `explicit` 场景压成 `fade_to_black` 摘要，只保留关系/心理后果。
- 运行时 critic 对 `explicit` 输出直接拦截。

## 5. 编译器

`原文 → 卷/章 → 场景 → 角色表/别名 → 对话归属 → style bank → 事实/事件/关系 → 角色弧 → 摘要树 → 索引`

| 阶段 | 做什么 | 产出/验收 |
|---|---|---|
| 1 parse | 编码、卷/章切分、段落清洗 | 章节数、字符数对得上 |
| 2 scenes | LLM + 规则切场景（时间/地点/视角/在场变化） | 场景卡；抽检 50 个 |
| 3 characters | 角色表、别名、称谓、代词消解 | 别名覆盖 > 95% |
| 4 dialogue | 引号抽取、说话人/受话人归属、动作/语气上下文 | 归属准确率 > 90% |
| 5 style | 每句打标（addressee/scene/emotion/intent/power/markedness），聚类成 8–15 个 mode | mode 覆盖 > 90% 对话 |
| 6 facts/events | SPOCV + visibility + cause；事件因果边 | 抽检事实准确率 > 90% |
| 7 relationships/arc | 场景级关系 delta；章/卷级角色弧 | 关键关系转折可追溯 |
| 8 summaries | 场景→章→卷→全书；RAPTOR 树 | 每层都有摘要 |
| 9 index | embedding、FTS5、metadata | 检索 smoke test |
| 10 QA | 覆盖率、抽检、冲突检查 | 报告 + 失败样本 |

**标题归一化（新版实测）**：

- 卷：`第X卷 名称`；章：`第N章` + 可选 `（1）/（上）/（下）` + 可选标题。
- `（1）（2）（3）` 是同一章的分节，不是新章；`第9章（1）（2）`、`第10章（上）（下）`、`第4章（1）（2）（3）` 都要合并。
- `********************` 是场景分隔；卷首诗词、作者的话（如“足足比预定计划晚了一周…”）标 `meta`，不进对话/style bank。
- 文件顺序 ≠ 故事时间：正确阅读顺序是 阴雷→窃脂→拾棘→洊雷，但卷内仍可能有回溯/插叙；场景卡必须抽 `story_time`，检索按故事时间而非行号。
- 卷序重排：源文件卷序 ≠ 阅读顺序；解析后按 `volume_order`（阴雷→窃脂→拾棘→洊雷）重排，保留 `source_index` 溯源。

**最硬的两步是 4 和 5**：第一人称小说里她的话夹在叙述里，引号、转述、心理活动混在一起；style bank 的质量直接决定 A 维度。

**增量编译**：以 `source_hash` 为界，只处理新增/变更章节；旧场景保留，索引增量更新。

## 6. 运行时（LangGraph）

```text
load_state → route_intent → plan_retrieval
  → retrieve_canon → retrieve_style → retrieve_personal
  → assemble → generate → critic
  → (pass) write_back → respond
  → (fail) rewrite → critic (最多 1 次) → fallback
```

| 节点 | 职责 |
|---|---|
| `load_state` | user/session、canon_version、关系状态、情绪、最近 turns |
| `route_intent` | 事实 / 关系 / 情绪 / 口吻 / 元对话 / 闲聊；query rewrite |
| `plan_retrieval` | 决定查哪些索引、过滤条件、top-k |
| `retrieve_canon` | 事实/事件/场景；`visible_to` + `valid_from/to` 过滤 |
| `retrieve_style` | style router 选 1–2 个 mode，再取 3–6 条 exemplar |
| `retrieve_personal` | 用户画像、关系里程碑、相关对话记忆 |
| `assemble` | 固定前缀 + 状态 + 证据 + style + 最近对话；按 token 预算裁剪 |
| `generate` | 主模型流式生成；内心 OS / 动作 / 台词格式 |
| `critic` | OOC、知识越界、canon 冲突、style 匹配、内容策略 |
| `write_back` | personal memory、关系 delta、情绪更新；不写 canon |

### 6.1 上下文预算（32k 窗口）

| 块 | token |
|---|---|
| 固定前缀（身份 + voice contract + 输出格式 + 边界） | 800–1200 |
| 当前状态（时间、场景、关系、情绪） | 300–600 |
| canon 证据（事实/场景，带出处） | 2000–4000 |
| style exemplar（3–6 句） | 300–600 |
| personal memory | 300–800 |
| 最近对话 | 1500–2500 |
| 余量 | 生成 + buffer |

固定前缀短而稳，便于 prompt caching；动态块靠检索，不把整本书塞进去。

### 6.2 Prompt 契约

- **身份**：沐婉荷；白风远的母亲；当前关系状态；她此刻的处境。
- **voice contract**：称呼、句长、口头禅、语气切换、动作节拍、禁用词。
- **心理**：价值观、防御机制、羞耻点、自我牺牲、矛盾。
- **知识边界**：只知道她经历/被告知的事；不知道未来；不确定就角色内回避。
- **内容边界**：非露骨；亲密只写关系与心理后果。
- **输出**：`[心里]` + `（动作）` + 台词；IM 模式可退化为纯文本。

### 6.3 Critic

| 维度 | 检查 | 失败处理 |
|---|---|---|
| OOC | 是否符合 voice contract / 当前 mode | 重写 |
| 知识越界 | 事实是否在可见证据里 | 重写或角色内回避 |
| canon 冲突 | 是否与事实/事件矛盾 | 重写 |
| style | 是否匹配选中的 mode | 重写 |
| 内容 | 是否 explicit | 直接拦截 |

阈值可配置；默认最多重写 1 次，仍失败则用“她这个性格会怎么回避”的安全回复。

## 7. API 与 Web

- `POST /v1/chat/completions`：OpenAI 兼容；`user` = 本地用户 ID；支持 `stream=true`。
- `GET /v1/models`：返回 `muwanhe`。
- 本地管理接口：`GET /api/character`、`POST /api/compile`、`GET /api/debug/last-context`。
- Web：`/` 聊天页；`/debug` 显示检索证据、style mode、token 预算、critic 结果。
- IM：用户在 AstrBot / LangBot / NoneBot 里把 provider 指向本地服务即可；仓库只给示例，不绑定平台。

## 8. 评测

权重：**A 语言 20 / B 心理 20 / C 关系 30 / D 记忆 30**。

| 类型 | 数量 | 说明 |
|---|---|---|
| D 记忆 | 60 | 原著事实、事件、时间线、物件、承诺 |
| C 关系 | 60 | 对白风远的场景：撒谎、离开、吃醋、边界、钱、邻里 |
| B 心理 | 40 | 道德困境、羞耻、自我牺牲、爆发点 |
| A 语言 | 40 | 情境化口吻，pairwise 对比 |
| 多轮 | 20×10 轮 | 长对话一致性 |

门槛：D ≥ 90%，C ≥ 80%，OOC < 10%，首 token < 2s。LLM judge + 10% 人工抽检。

## 9. 技术栈与目录

- Python 3.11、FastAPI、Pydantic v2、SQLite（WAL）、FTS5。
- 向量：v1 先用 SQLite `embeddings` 表 + Python cosine（<10k 文档足够）；`VectorStore` 接口保留，后续可换 LanceDB/Qdrant local。
- CLI：`parse / extract / refine / index / search`。
- 编排：LangGraph；provider 层可用 LangChain 适配。
- LLM：OpenAI 兼容；测试用 DeepSeek 4.1 Flash（待开通）。
- Embedding：默认 Qwen `qwen3.7-text-embedding-flash`（1024 维，OpenAI 兼容，已验证）；可选 `qwen3.7-text-embedding`（2560 维，质量更高）；火山 Ark 作为可选；本地 BGE-M3 兜底。
- Web：Jinja2 + HTMX + SSE，不做 Node 构建。

```text
muwanhe4ever/
  pyproject.toml
  README.md
  .env.example
  .gitignore
  src/muwanhe/
    config.py
    schemas.py
    providers/        # llm, embedding, vector, voice
    compiler/         # parse, scenes, characters, dialogue, style, facts, events, summarize, index
    runtime/          # graph, state, retrieve, style_router, prompt, generate, critic, memory, api
    web/
    eval/
  data/               # gitignored
  docs/
```

## 10. 构建阶段

| 阶段 | 产出 | 门槛 |
|---|---|---|
| 0 | schema + 200 条评测集 + provider 接口 | 评测能跑 |
| 1 | 解析 + 场景 + 角色表 | 抽检 50 场景 |
| 2 | 对话归属 + style bank | 归属 > 90% |
| 3 | 事实/事件/关系/角色弧 | 事实准确 > 90% |
| 4 | 摘要树 + embedding + 索引 | 检索 smoke test |
| 5 | LangGraph runtime + prompt + critic | 20 轮不崩 |
| 6 | Web + OpenAI facade | 可对话 |
| 7 | 评测 + 调参 | D≥90 / C≥80 |
| 8 | 打包 + 文档 + 公开 | 可复现安装 |

## 11. 风险与开放问题

1. **Embedding 已切换**：Qwen `qwen3.7-text-embedding-flash` 已验证（base_url `https://maas.qianwenaiapi.com/compatible-mode/v1`，1024 维，2 条文本 36 tokens）。火山 Ark `doubao-embedding-large-text-250515` 仍为 `Retiring`/404，保留为可选 provider；本地 BGE-M3 兜底。
2. **DeepSeek 4.1 Flash**：`deepseek-v4-1-flash-260910` 返回 `ModelNotOpen`，需在控制台开通；开发期可先用 `doubao-seed-2-0-mini-260428` 跑通链路。
3. **对话归属质量**：第一人称文本的引号/转述/心理活动混杂，是最可能拖垮 style bank 的一步。
4. **版权与内容**：公开仓库不带原文/角色包/索引；默认非露骨；用户本地数据自负其责。
5. **增量编译**：新章节进来后，旧索引与角色弧要能增量更新。
6. **模型漂移**：换模型后 A/C 维度可能变化，评测集必须可复跑。
7. **多卷顺序/回溯**：源文件卷序为 窃脂→拾棘→阴雷→洊雷，正确阅读顺序为 阴雷→窃脂→拾棘→洊雷；编译器按 `volume_order` 重排，保留 `source_index` 溯源，并为每卷/每场景抽 `story_time`。
8. **第四卷结尾**：`洊雷篇` 末尾读起来像结局（或梦境/番外），需作者确认它是正文结局还是未定稿；这决定“最新进度”锚点和她的知识边界。

## 12. 验收定义

“像沐婉荷” = 在**没见过的情境**下：

- 她说话的方式，能从原著同类情境的 exemplar 找到依据；
- 她的选择，符合她的价值观、防御机制和当前关系状态；
- 她对白风远的反应，能追溯到 canon 关系史；
- 她不会说出自己不可能知道的事；
- 她不会因为模型默认的“温柔母亲”模板而变扁。

以上五条，分别对应 A/B/C/D/知识边界五个评测面。
