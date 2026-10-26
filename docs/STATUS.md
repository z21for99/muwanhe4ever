# 项目状态 / 交接

更新时间：2026-10-26

## 一句话

本地优先的《花嫁》沐婉荷角色运行时：解析 → 对话提取 → 场景分段 → 向量/FTS 检索 → style bank → 角色 prompt/engine → OpenAI 兼容 API + Web。

仓库不含原著文本、角色包、向量索引或 key；这些都在本地 `data/`，已 gitignore。

## 已验证

```powershell
python -m pytest -q   # 69 passed
```

- 121 个 scene、703 个最新 segment 已建向量（Qwen `qwen3.7-text-embedding-flash`，1024 维）
- FTS5 trigram 覆盖同样 121 scene + 703 segment；中文 2 字查询走 `LIKE` 兜底
- scene 检索 leave-one-out：向量 top1 0.85 / top5 0.90；FTS exact-substring top1 1.0
- strict 对话 4,134 条；高精度沐婉荷 style 样本 223 条
- attribution 44 条 gold（2 个场景）：accuracy 0.500 / coverage 0.386 / precision 0.529
- API：`/v1/chat/completions`（支持 `stream=true`）、`/v1/models`、`/health`
- session：`user` 作为 key，自动存/取 history；`GET/DELETE /api/session/{id}`
- Web：`/` 自动加载历史 + “重新开始”
- 错误处理：embedding 429、Ark 403 欠费都会返回清晰错误，不抛 traceback

## 常用命令

```powershell
# 解析（卷序必须阴雷→窃脂→拾棘→洊雷）
python -m muwanhe.cli parse --input "花嫁(2).txt" --db "data/muwanhe.db" `
  --volume-order "阴雷篇,窃脂篇,拾棘篇,洊雷篇"

# 严格归属
python -m muwanhe.cli extract --db "data/muwanhe.db" --strict

# 分段（可分批）
python -m muwanhe.cli refine --db "data/muwanhe.db" --segments-only --limit 30 --offset 0

# 向量索引（Qwen 免费额度容易 429；建议 20 段/批）
python -m muwanhe.cli index --db "data/muwanhe.db" --kind segment --limit 20 --offset 0

# FTS 索引（不耗 embedding 额度）
python -m muwanhe.cli index-fts --db "data/muwanhe.db"

# style bank
python -m muwanhe.cli style --db "data/muwanhe.db" --min-samples 3

# 评估
python -m muwanhe.cli eval-retrieval --db "data/muwanhe.db" --limit 20
python -m muwanhe.cli eval-retrieval --db "data/muwanhe.db" --mode fts --limit 20
python -m muwanhe.cli eval-attribution --db "data/muwanhe.db" --gold "eval/attribution_gold.json"

# 启动 Web + API
python -m muwanhe.cli serve --db "data/muwanhe.db" --model "doubao-seed-2-0-mini-260428"
```

## 当前阻塞

1. **火山 Ark 账户欠费**：`403 AccountOverdueError`，live chat 返回 503；需要结算后恢复。
2. **Qwen embedding 免费额度有限**：全量重建建议 `--limit 20 --offset ...` 分批；一次性 703 段会 429。
3. **attribution recall 低**：strict coverage 0.386；多人物场景（孙淑怡等）里 `我/她` cue 会抢话。需要更强模型或人工复核，不要继续硬调规则过拟合 14 条 gold。
4. **DeepSeek 4.1 Flash 未开通**：当前 LLM 只能用 Doubao mini（且欠费）。

## 下一步建议

- Ark 结算后，用 44 条 gold 对比 mini / DeepSeek 的 LLM 归属，优先修多人物场景。
- style bank 人工抽检 223 条，按 `utterance_id` 建排除表，而不是继续加正则。
- 公开仓库前再确认：无 `.env`、无 `data/`、无原著片段、无角色包。

## Git

- 本地 `main` 可能领先远端（网络 reset 时）：`git status --short --branch`
- 推送：`git -c http.version=HTTP/1.1 push origin main`
- 当前本地：`1f8d51d`（含本文件）；远端：`6606fd6`（以 `git status` 为准）
