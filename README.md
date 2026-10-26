# muwanhe4ever

本地优先的长篇小说角色运行时。目标不是“角色卡聊天”，而是把一部长篇小说的场景、对话、关系和口吻编译成可检索、可评测的角色记忆，让角色在**最新连载进度**上，以她自己的心理和语言逻辑与用户对话。

当前是 v0.1：解析、对话提取、场景索引、风格样本、本地角色引擎和 OpenAI 兼容 API 已经跑通；speaker 归属和风格标签仍是实验性的。

## 当前能做什么

- 解析长篇小说：卷 / 章 / 分节 / 场景（支持乱序卷重排）
- 提取引号对话并做规则归属：cue / voice / vocative，其余标 `unverified`
- 场景 + 分节的向量索引、语义检索；FTS5 trigram 关键词兜底（embedding 配额用尽也能检索）
- 从高置信度对话里构建 style bank（风格样本）
- 本地角色引擎：检索原著片段 + style bank + 角色核心 → LLM
- 服务端 session 记忆：OpenAI 请求里的 `user` 作为 session key，自动保存多轮 history；Web 页打开时自动加载历史
- OpenAI 兼容 `/v1/chat/completions`（支持 `stream=true`），以及一个本地 Web 聊天页

## 快速开始

```powershell
python -m pip install -e ".[dev]"

# 1. 配置 key（.env 不会进 git）
Copy-Item .env.example .env
# 填 QWEN_API_KEY、ARK_API_KEY；模型可用 --model 覆盖

# 2. 解析小说（把 花嫁(2).txt 放在本地，不要提交）
python -m muwanhe.cli parse --input "花嫁(2).txt" --db "data/muwanhe.db" `
  --volume-order "阴雷篇,窃脂篇,拾棘篇,洊雷篇"

# 3. 提取对话；strict 只保留高置信度归属
python -m muwanhe.cli extract --db "data/muwanhe.db" --strict

# 4. 索引场景
python -m muwanhe.cli index --db "data/muwanhe.db" --kind scene

# 5. 构建 style bank（默认 precision 模式）
python -m muwanhe.cli style --db "data/muwanhe.db" --min-samples 3

# 6. 可选：把角色档案写到 data/muwanhe_profile.md，serve/chat 会自动加载
# 7. 启动本地 Web + OpenAI 兼容 API
python -m muwanhe.cli serve --db "data/muwanhe.db" --model "doubao-seed-2-0-mini-260428"
# 打开 http://127.0.0.1:8000
```

## OpenAI 兼容调用

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"muwanhe","messages":[{"role":"user","content":"我回来了"}]}'
```

把 AstrBot / LangBot / Open WebUI 等 IM 或前端工具的 provider 指向这个本地地址即可；`user` 字段预留给后续多用户隔离。

## 数据与边界

- 原著文本、`.env`、`data/`、SQLite、向量都在本地，已 gitignore。
- 公开仓库只包含引擎、schema、测试和中性 Web 页。
- 角色数据由用户自己的文本生成，不随仓库分发。
- 默认非露骨内容；亲密场景只保留关系和心理后果。

## 测试

```powershell
python -m pytest -q
```

## 目录

```text
src/muwanhe/
  api.py            OpenAI 兼容 API + Web 入口
  web.py            本地聊天页
  cli.py            parse / extract / refine / index / search / style / chat / serve
  compiler/         parse / dialogue / attribution / extract / refine / index / style
  providers/        LLM / embedding
  runtime/          prompt + character engine
  storage/          SQLite parse / extraction / vector store
tests/
docs/superpowers/  design spec + plans
```

## 当前指标

- 66 个单元测试通过。
- scene 检索（20 场景 leave-one-out）：向量 top1 0.85 / top5 0.90；FTS exact-substring top1 1.0。
- strict 对话：4,134 条；高精度沐婉荷台词 224 条（window=8）。
- 场景分段：725 段已生成；FTS 已索引 121 scene + 703 segment。
- attribution gold（14 条）：accuracy 0.571 / coverage 0.643 / precision 0.889。

## 已知问题

- speaker 归属的 strict 模式 precision 高（0.889），但 coverage 只有 0.643；还有 5 条 gold 引语未覆盖，需要更强模型或人工复核。
- 向量索引只覆盖 121 scene + 68 segment；剩余 657 段用 FTS5 关键词兜底，语义检索需等 Qwen 额度或本地 BGE-M3。
- LLM 复核使用 `doubao-seed-2-0-mini` 时归属质量不足；DeepSeek 4.1 Flash 尚未开通。
- API 支持 `stream=true` SSE；Web 页仍是一次性返回。
